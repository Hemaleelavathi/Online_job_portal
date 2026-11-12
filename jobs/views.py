from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.decorators import render_access_denied, role_required
from accounts.files import serve_pdf_file
from accounts.models import UserProfile

from .forms import ApplicationStatusForm, JobApplicationForm, JobForm
from .models import Job, JobApplication, SavedJob


def _get_owned_job_or_403(request, job_id):
    """Return a Job owned by request.user or a 403 response if owned by another user."""
    job = get_object_or_404(Job, pk=job_id)
    if job.employer_id != request.user.id:
        return None, render_access_denied(request, 'the owner of this job posting')
    return job, None


def _get_manageable_application_or_403(request, application_id):
    """Return a JobApplication manageable by the owning employer or staff admin, or a 403 response."""
    application = get_object_or_404(
        JobApplication.objects.select_related('job', 'applicant', 'applicant__profile'),
        pk=application_id,
    )
    if request.user.is_staff:
        return application, None

    profile = getattr(request.user, 'profile', None)
    if profile is None or profile.role != UserProfile.ROLE_EMPLOYER:
        return None, render_access_denied(request, 'Employer or Admin')

    if application.job.employer_id != request.user.id:
        return None, render_access_denied(request, 'the employer who owns this job posting')

    return application, None


def _filter_active_jobs(request):
    """Filter active jobs by optional query, location, and job_type GET parameters."""
    query = request.GET.get('q', '').strip()
    location = request.GET.get('location', '').strip()
    job_type = request.GET.get('job_type', '').strip()

    jobs = Job.objects.filter(is_active=True)
    if query:
        jobs = jobs.filter(
            Q(title__icontains=query)
            | Q(company__icontains=query)
            | Q(description__icontains=query)
            | Q(job_type__icontains=query)
            | Q(skills_required__icontains=query)
            | Q(experience__icontains=query)
        )
    if location:
        jobs = jobs.filter(
            Q(location__icontains=location) | Q(job_type__icontains=location)
        )
    if job_type:
        jobs = jobs.filter(job_type=job_type)

    return jobs, query, location, job_type


def _get_applied_job_ids(user):
    """Return IDs of jobs the user has applied for, or an empty set if unauthenticated."""
    if not user.is_authenticated:
        return set()
    return set(JobApplication.objects.filter(applicant=user).values_list('job_id', flat=True))


def _get_saved_job_ids(user):
    """Return IDs of jobs saved by an authenticated user, or an empty set."""
    if not user.is_authenticated:
        return set()
    return set(SavedJob.objects.filter(user=user).values_list('job_id', flat=True))


def _safe_redirect_url(request, candidate, fallback_name):
    """Return candidate URL if safe on this host, otherwise fallback route name."""
    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return fallback_name


def home(request):
    """Render the CareerConnect home page with optional search filtering and live metrics."""
    jobs, query, location, _ = _filter_active_jobs(request)
    active_jobs_qs = Job.objects.filter(is_active=True)

    return render(
        request,
        'home.html',
        {
            'featured_jobs': jobs,
            'search_query': query,
            'search_location': location,
            'is_filtered': bool(query or location),
            'applied_job_ids': _get_applied_job_ids(request.user),
            'saved_job_ids': _get_saved_job_ids(request.user),
            'active_jobs_count': active_jobs_qs.count(),
            'total_companies_count': active_jobs_qs.values('company').distinct().count(),
            'total_applications_count': JobApplication.objects.count(),
        },
    )


def job_list(request):
    """Display all active job postings with job title, location, and job-type filtering."""
    jobs, query, location, job_type = _filter_active_jobs(request)

    return render(
        request,
        'jobs/job_list.html',
        {
            'jobs': jobs,
            'job_type_choices': Job.JOB_TYPE_CHOICES,
            'search_query': query,
            'search_location': location,
            'selected_job_type': job_type,
            'is_filtered': bool(query or location or job_type),
            'applied_job_ids': _get_applied_job_ids(request.user),
            'saved_job_ids': _get_saved_job_ids(request.user),
        },
    )


def job_detail(request, job_id):
    """Display complete job details and inline application form for eligible Job Seekers."""
    job = get_object_or_404(Job, pk=job_id)
    is_owner = request.user.is_authenticated and job.employer_id == request.user.id
    is_staff = request.user.is_authenticated and request.user.is_staff

    existing_application = None
    if request.user.is_authenticated:
        existing_application = JobApplication.objects.filter(
            job=job,
            applicant=request.user,
        ).first()
    has_applied = existing_application is not None

    if not job.is_active and not is_owner and not has_applied and not is_staff:
        raise Http404('Job posting not found.')
    is_job_seeker = (
        request.user.is_authenticated
        and getattr(getattr(request.user, 'profile', None), 'role', None) == UserProfile.ROLE_JOB_SEEKER
    )
    is_saved = (
        is_job_seeker
        and SavedJob.objects.filter(user=request.user, job=job).exists()
    )

    return render(
        request,
        'jobs/job_detail.html',
        {
            'job': job,
            'is_owner': is_owner,
            'has_applied': has_applied,
            'is_saved': is_saved,
            'existing_application': existing_application,
            'application_form': JobApplicationForm() if (is_job_seeker and not has_applied) else None,
        },
    )


@role_required(UserProfile.ROLE_JOB_SEEKER)
def apply_to_job(request, job_id):
    """Render the application/resume upload form and save Job Seeker applications."""
    job = get_object_or_404(Job, pk=job_id, is_active=True)
    next_url = request.POST.get('next') or request.GET.get('next', '')

    if JobApplication.objects.filter(job=job, applicant=request.user).exists():
        messages.info(request, f'You have already applied for {job.title} at {job.company}.')
        fallback = 'job_detail' if request.method == 'GET' else 'job_seeker_dashboard'
        target = _safe_redirect_url(request, next_url, fallback)
        return redirect(target, job_id=job.id) if target == 'job_detail' else redirect(target)

    if request.method == 'POST':
        form = JobApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            application = form.save(commit=False)
            application.job = job
            application.applicant = request.user
            try:
                application.save()
            except IntegrityError:
                messages.info(request, f'You have already applied for {job.title} at {job.company}.')
            else:
                messages.success(request, f'Application submitted for {job.title} at {job.company}.')
            return redirect(_safe_redirect_url(request, next_url, 'job_seeker_dashboard'))

        messages.error(request, 'Please correct the errors in your application form.')
    else:
        form = JobApplicationForm()

    return render(
        request,
        'jobs/apply_job.html',
        {
            'job': job,
            'form': form,
            'profile': request.user.profile,
            'next': next_url,
        },
    )


@role_required(UserProfile.ROLE_JOB_SEEKER)
def applied_jobs(request):
    """Display all jobs applied to by the logged-in Job Seeker with status and history."""
    base_applications = (
        JobApplication.objects.filter(applicant=request.user)
        .select_related('job', 'applicant__profile')
        .prefetch_related('status_history')
    )
    status_summary = JobApplication.status_summary(base_applications)
    applications, selected_status, is_valid = JobApplication.filter_by_status(
        base_applications,
        request.GET.get('status'),
    )
    if not is_valid:
        messages.error(request, 'Invalid application status filter specified.')
        return redirect('applied_jobs')

    return render(
        request,
        'jobs/applied_jobs.html',
        {
            'applications': applications,
            'total_applications': base_applications.count(),
            'status_summary': status_summary,
            'selected_status': selected_status,
            'profile': request.user.profile,
        },
    )


@login_required
@require_POST
def update_application_status(request, application_id):
    """Allow an owning Employer or staff Admin to update an application's status."""
    application, forbidden = _get_manageable_application_or_403(request, application_id)
    if forbidden:
        return forbidden

    form = ApplicationStatusForm(request.POST)
    if form.is_valid():
        new_status = form.cleaned_data['status']
        applicant_profile = getattr(application.applicant, 'profile', None)
        applicant_name = (
            applicant_profile.full_name
            if applicant_profile and applicant_profile.full_name
            else application.applicant.email
        )
        if application.update_status(new_status, changed_by=request.user):
            messages.success(
                request,
                f'Application status for {applicant_name} ({application.job.title}) updated to {application.get_status_display()}.',
            )
        else:
            messages.info(
                request,
                f'Application status for {applicant_name} is already {application.get_status_display()}.',
            )
    else:
        messages.error(request, 'Please select a valid application status.')

    default_fallback = 'admin_dashboard' if request.user.is_staff else 'employer_dashboard'
    redirect_target = _safe_redirect_url(
        request,
        request.POST.get('next', ''),
        default_fallback,
    )
    return redirect(redirect_target)


@login_required
def download_applicant_resume(request, application_id):
    """Serve the applicant's PDF resume to the hiring employer, applicant, or admin staff."""
    application = get_object_or_404(
        JobApplication.objects.select_related('job', 'applicant', 'applicant__profile'),
        pk=application_id,
    )
    is_hiring_employer = application.job.employer_id == request.user.id
    is_applicant = application.applicant_id == request.user.id
    if not (is_hiring_employer or is_applicant or request.user.is_staff):
        return render_access_denied(request, 'the hiring employer, applicant, or admin')

    return serve_pdf_file(
        application.effective_resume,
        filename=application.resume_filename,
        inline=(request.GET.get('inline') == '1'),
    )


@role_required(UserProfile.ROLE_JOB_SEEKER)
def saved_jobs(request):
    """Display all jobs bookmarked by the logged-in Job Seeker."""
    bookmarks = (
        SavedJob.objects.filter(user=request.user)
        .select_related('job', 'job__employer', 'job__employer__profile')
    )
    return render(
        request,
        'jobs/saved_jobs.html',
        {
            'saved_jobs': bookmarks,
            'applied_job_ids': _get_applied_job_ids(request.user),
            'profile': request.user.profile,
        },
    )


@role_required(UserProfile.ROLE_JOB_SEEKER)
@require_POST
def save_job(request, job_id):
    """Bookmark an active job for the logged-in Job Seeker while preventing duplicates."""
    job = get_object_or_404(Job, pk=job_id, is_active=True)
    try:
        _, created = SavedJob.objects.get_or_create(user=request.user, job=job)
    except IntegrityError:
        created = False

    if created:
        messages.success(request, f'"{job.title}" saved to your Saved Jobs.')
    else:
        messages.info(request, f'"{job.title}" is already in your Saved Jobs.')

    redirect_target = _safe_redirect_url(
        request,
        request.POST.get('next', ''),
        'saved_jobs',
    )
    return redirect(redirect_target)


@role_required(UserProfile.ROLE_JOB_SEEKER)
@require_POST
def unsave_job(request, job_id):
    """Remove a bookmarked job from the logged-in Job Seeker's Saved Jobs list."""
    bookmark = SavedJob.objects.select_related('job').filter(
        user=request.user,
        job_id=job_id,
    ).first()
    if bookmark:
        title = bookmark.job.title
        bookmark.delete()
        messages.info(request, f'Removed "{title}" from your Saved Jobs.')

    redirect_target = _safe_redirect_url(
        request,
        request.POST.get('next', ''),
        'saved_jobs',
    )
    return redirect(redirect_target)


@role_required(UserProfile.ROLE_EMPLOYER)
def create_job(request):
    """Allow an Employer to create and publish a new job posting."""
    profile = request.user.profile

    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.employer = request.user
            job.save()
            messages.success(request, f'Job "{job.title}" posted successfully.')
            return redirect('employer_dashboard')
        messages.error(request, 'Please correct the errors in the job form below.')
    else:
        initial = {}
        if profile.company_name:
            initial['company'] = profile.company_name
        if profile.location:
            initial['location'] = profile.location
        form = JobForm(initial=initial)

    return render(
        request,
        'jobs/job_form.html',
        {'form': form, 'is_edit': False},
    )


@role_required(UserProfile.ROLE_EMPLOYER)
def edit_job(request, job_id):
    """Allow an Employer to edit one of their own job postings."""
    job, forbidden = _get_owned_job_or_403(request, job_id)
    if forbidden:
        return forbidden

    if request.method == 'POST':
        form = JobForm(request.POST, instance=job)
        if form.is_valid():
            updated_job = form.save()
            messages.success(request, f'Job "{updated_job.title}" updated successfully.')
            return redirect('employer_dashboard')
        messages.error(request, 'Please correct the errors in the job form below.')
    else:
        form = JobForm(instance=job)

    return render(
        request,
        'jobs/job_form.html',
        {'form': form, 'job': job, 'is_edit': True},
    )


@role_required(UserProfile.ROLE_EMPLOYER)
def delete_job(request, job_id):
    """Allow an Employer to confirm and delete one of their own job postings."""
    job, forbidden = _get_owned_job_or_403(request, job_id)
    if forbidden:
        return forbidden

    if request.method == 'POST':
        title = job.title
        job.delete()
        messages.success(request, f'Job "{title}" deleted successfully.')
        return redirect('employer_dashboard')

    return render(request, 'jobs/job_confirm_delete.html', {'job': job})

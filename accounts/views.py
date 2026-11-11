from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from jobs.models import Job, JobApplication

from .decorators import (
    get_dashboard_url_name,
    render_access_denied,
    role_required,
    staff_required,
)
from .forms import EmployerProfileForm, JobSeekerProfileForm, LoginForm, RegistrationForm
from .models import UserProfile

User = get_user_model()


def register(request):
    """Handle user registration form display, validation, and account creation."""
    if request.user.is_authenticated:
        return redirect(get_dashboard_url_name(request.user))

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            try:
                form.save()
            except IntegrityError:
                form.add_error('email', 'An account with this email address already exists.')
                messages.error(request, 'Please correct the errors highlighted below.')
            else:
                messages.success(
                    request,
                    'Registration successful! You can now log in with your email and password.',
                )
                return redirect('login')
        else:
            messages.error(request, 'Please correct the errors highlighted below.')
    else:
        form = RegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    """Authenticate a user with email and password and redirect by role."""
    if request.user.is_authenticated:
        return redirect(get_dashboard_url_name(request.user))

    next_url = request.POST.get('next') or request.GET.get('next', '')

    if request.method == 'POST':
        form = LoginForm(request=request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            profile = getattr(user, 'profile', None)
            display_name = (profile.full_name if profile else '') or user.get_full_name() or user.email
            messages.success(request, f'Welcome back, {display_name}!')

            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)

            return redirect(get_dashboard_url_name(user))

        non_field_errors = form.non_field_errors()
        error_msg = non_field_errors[0] if non_field_errors else 'Please enter a valid email address and password.'
        messages.error(request, error_msg)
    else:
        form = LoginForm(request=request)

    return render(request, 'accounts/login.html', {'form': form, 'next': next_url})


@require_POST
def logout_view(request):
    """Log out the current user, clear the session, and redirect to login."""
    if request.user.is_authenticated:
        logout(request)
        messages.success(request, 'You have been logged out successfully.')
    return redirect('login')


@login_required
def dashboard_redirect(request):
    """Route an authenticated user to their role-specific or admin dashboard."""
    target = get_dashboard_url_name(request.user)
    if target == 'home':
        messages.info(request, 'No portal profile is assigned to this account.')
    return redirect(target)


@role_required(UserProfile.ROLE_JOB_SEEKER)
def job_seeker_dashboard(request):
    """Render the protected Job Seeker dashboard with profile updates, resume upload, and jobs."""
    profile = request.user.profile

    if request.method == 'POST':
        form = JobSeekerProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('job_seeker_dashboard')
        messages.error(request, 'Please correct the errors in your profile form below.')
    else:
        form = JobSeekerProfileForm(instance=profile)

    available_jobs = Job.objects.filter(is_active=True)
    base_applications = (
        JobApplication.objects.filter(applicant=request.user)
        .select_related('job', 'applicant__profile')
        .prefetch_related('status_history')
    )
    applied_job_ids = set(base_applications.values_list('job_id', flat=True))
    status_summary = JobApplication.status_summary(base_applications)
    applications, selected_status, is_valid = JobApplication.filter_by_status(
        base_applications,
        request.GET.get('status'),
    )
    if not is_valid:
        messages.error(request, 'Invalid application status filter specified.')
        return redirect('job_seeker_dashboard')

    return render(
        request,
        'accounts/job_seeker_dashboard.html',
        {
            'profile': profile,
            'form': form,
            'available_jobs': available_jobs,
            'applications': applications,
            'total_applications': base_applications.count(),
            'status_summary': status_summary,
            'selected_status': selected_status,
            'applied_job_ids': applied_job_ids,
        },
    )


@role_required(UserProfile.ROLE_EMPLOYER)
def employer_dashboard(request):
    """Render the protected Employer dashboard with company profile, job management, and applicants."""
    profile = request.user.profile

    if request.method == 'POST':
        form = EmployerProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Company details updated successfully.')
            return redirect('employer_dashboard')
        messages.error(request, 'Please correct the errors in your company details form below.')
    else:
        form = EmployerProfileForm(instance=profile)

    posted_jobs = Job.objects.filter(employer=request.user).annotate(
        applicant_count=Count('applications')
    )
    all_employer_applications = (
        JobApplication.objects.filter(job__employer=request.user)
        .select_related('job', 'applicant', 'applicant__profile')
        .prefetch_related('status_history')
    )

    selected_job = None
    selected_job_id = request.GET.get('job', '').strip()
    if selected_job_id:
        if not selected_job_id.isdigit():
            messages.error(request, 'Invalid job filter specified.')
            return redirect('employer_dashboard')
        selected_job = get_object_or_404(Job, pk=int(selected_job_id))
        if selected_job.employer_id != request.user.id:
            return render_access_denied(request, 'the owner of that job posting')
        scoped_applications = all_employer_applications.filter(job=selected_job)
    else:
        scoped_applications = all_employer_applications

    status_summary = JobApplication.status_summary(scoped_applications)
    applications, selected_status, is_valid = JobApplication.filter_by_status(
        scoped_applications,
        request.GET.get('status'),
    )
    if not is_valid:
        messages.error(request, 'Invalid application status filter specified.')
        return redirect('employer_dashboard')

    return render(
        request,
        'accounts/employer_dashboard.html',
        {
            'profile': profile,
            'form': form,
            'posted_jobs': posted_jobs,
            'applications': applications,
            'selected_job': selected_job,
            'selected_status': selected_status,
            'status_choices': JobApplication.STATUS_CHOICES,
            'status_summary': status_summary,
            'scoped_applications_count': scoped_applications.count(),
            'total_applicants': all_employer_applications.count(),
        },
    )


@staff_required
def admin_dashboard(request):
    """Render the protected Admin Dashboard with platform totals and application management."""
    total_users = User.objects.count()
    total_employers = UserProfile.objects.filter(role=UserProfile.ROLE_EMPLOYER).count()
    total_job_seekers = UserProfile.objects.filter(role=UserProfile.ROLE_JOB_SEEKER).count()
    total_staff = User.objects.filter(is_staff=True).count()

    total_jobs = Job.objects.count()
    active_jobs_count = Job.objects.filter(is_active=True).count()
    inactive_jobs_count = total_jobs - active_jobs_count
    total_applications = JobApplication.objects.count()

    recent_users = User.objects.select_related('profile').order_by('-date_joined')[:5]
    all_jobs = Job.objects.select_related('employer', 'employer__profile').annotate(
        applicant_count=Count('applications')
    )
    recent_jobs = all_jobs[:6]

    base_applications = (
        JobApplication.objects.select_related(
            'job',
            'job__employer',
            'job__employer__profile',
            'applicant',
            'applicant__profile',
        )
        .prefetch_related('status_history')
    )

    search_query = request.GET.get('q', '').strip()
    scoped_applications = base_applications
    if search_query:
        scoped_applications = scoped_applications.filter(
            Q(applicant__profile__full_name__icontains=search_query)
            | Q(applicant__email__icontains=search_query)
            | Q(job__title__icontains=search_query)
            | Q(job__company__icontains=search_query)
        )

    selected_job = None
    selected_job_id = request.GET.get('job', '').strip()
    if selected_job_id:
        if not selected_job_id.isdigit():
            messages.error(request, 'Invalid job filter specified.')
            return redirect('admin_dashboard')
        selected_job = get_object_or_404(Job, pk=int(selected_job_id))
        scoped_applications = scoped_applications.filter(job=selected_job)

    status_summary = JobApplication.status_summary(scoped_applications)
    applications, selected_status, is_valid = JobApplication.filter_by_status(
        scoped_applications,
        request.GET.get('status'),
    )
    if not is_valid:
        messages.error(request, 'Invalid application status filter specified.')
        return redirect('admin_dashboard')

    return render(
        request,
        'accounts/admin_dashboard.html',
        {
            'total_users': total_users,
            'total_employers': total_employers,
            'total_job_seekers': total_job_seekers,
            'total_staff': total_staff,
            'total_jobs': total_jobs,
            'active_jobs_count': active_jobs_count,
            'inactive_jobs_count': inactive_jobs_count,
            'total_applications': total_applications,
            'recent_users': recent_users,
            'recent_jobs': recent_jobs,
            'all_jobs': all_jobs,
            'applications': applications,
            'search_query': search_query,
            'selected_job': selected_job,
            'selected_status': selected_status,
            'status_choices': JobApplication.STATUS_CHOICES,
            'status_summary': status_summary,
            'scoped_applications_count': scoped_applications.count(),
        },
    )

from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html

from .models import ApplicationStatusHistory, Job, JobApplication, SavedJob


def _bulk_update_status(modeladmin, request, queryset, status_code, status_label):
    """Update selected JobApplications to status_code and record status history."""
    updated_count = 0
    for application in queryset.select_related('applicant', 'job'):
        if application.update_status(status_code, changed_by=request.user):
            updated_count += 1
    modeladmin.message_user(
        request,
        f'Updated {updated_count} application(s) to {status_label}.',
        level=messages.SUCCESS,
    )


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'location', 'job_type', 'experience', 'employer', 'is_active', 'posted_date')
    list_filter = ('job_type', 'is_active', 'posted_date')
    search_fields = ('title', 'company', 'location', 'skills_required', 'experience')


class ApplicationStatusHistoryInline(admin.TabularInline):
    model = ApplicationStatusHistory
    extra = 0
    can_delete = False
    readonly_fields = ('status', 'changed_by', 'changed_at')

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    """Admin interface for viewing, filtering, searching, and managing job applications."""

    list_display = (
        'applicant_name',
        'applicant_email',
        'job_title',
        'job_company',
        'application_date',
        'status',
        'resume_link',
    )
    list_display_links = ('applicant_name', 'job_title')
    list_editable = ('status',)
    list_filter = ('status', 'applied_at')
    date_hierarchy = 'applied_at'
    search_fields = (
        'applicant__profile__full_name',
        'applicant__first_name',
        'applicant__last_name',
        'applicant__email',
        'job__title',
        'job__company',
    )
    list_select_related = ('job', 'applicant', 'applicant__profile')
    readonly_fields = (
        'applicant_name',
        'applicant_email',
        'applied_at',
        'status_updated_at',
        'resume_link',
    )
    fieldsets = (
        ('Applicant & Job', {
            'fields': ('job', 'applicant', 'applicant_name', 'applicant_email'),
        }),
        ('Application Status & Timeline', {
            'fields': ('status', 'applied_at', 'status_updated_at'),
        }),
        ('Resume & Cover Note', {
            'fields': ('resume', 'resume_link', 'cover_note'),
        }),
    )
    inlines = [ApplicationStatusHistoryInline]
    actions = (
        'mark_as_applied',
        'mark_as_shortlisted',
        'mark_as_rejected',
        'mark_as_selected',
    )

    @admin.display(description='Applicant Name', ordering='applicant__profile__full_name')
    def applicant_name(self, obj):
        if not obj or not getattr(obj, 'applicant_id', None):
            return '-'
        profile = getattr(obj.applicant, 'profile', None)
        if profile and profile.full_name:
            return profile.full_name
        return obj.applicant.get_full_name() or obj.applicant.email or obj.applicant.username

    @admin.display(description='Email', ordering='applicant__email')
    def applicant_email(self, obj):
        if not obj or not getattr(obj, 'applicant_id', None):
            return '-'
        return obj.applicant.email

    @admin.display(description='Job Title', ordering='job__title')
    def job_title(self, obj):
        return obj.job.title if obj and getattr(obj, 'job_id', None) else '-'

    @admin.display(description='Company', ordering='job__company')
    def job_company(self, obj):
        return obj.job.company if obj and getattr(obj, 'job_id', None) else '-'

    @admin.display(description='Application Date', ordering='applied_at')
    def application_date(self, obj):
        return obj.applied_at

    @admin.display(description='Uploaded Resume')
    def resume_link(self, obj):
        if not obj or not obj.pk or not obj.effective_resume:
            return 'No resume uploaded'
        view_url = f"{reverse('download_applicant_resume', args=[obj.id])}?inline=1"
        download_url = reverse('download_applicant_resume', args=[obj.id])
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">View Resume</a>'
            ' &nbsp;|&nbsp; '
            '<a href="{}">Download</a>',
            view_url,
            download_url,
        )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change and 'status' in getattr(form, 'changed_data', ()):
            ApplicationStatusHistory.objects.create(
                application=obj,
                status=obj.status,
                changed_by=request.user,
            )

    @admin.action(description='Mark selected applications as Applied')
    def mark_as_applied(self, request, queryset):
        _bulk_update_status(self, request, queryset, JobApplication.STATUS_APPLIED, 'Applied')

    @admin.action(description='Mark selected applications as Shortlisted')
    def mark_as_shortlisted(self, request, queryset):
        _bulk_update_status(self, request, queryset, JobApplication.STATUS_SHORTLISTED, 'Shortlisted')

    @admin.action(description='Mark selected applications as Rejected')
    def mark_as_rejected(self, request, queryset):
        _bulk_update_status(self, request, queryset, JobApplication.STATUS_REJECTED, 'Rejected')

    @admin.action(description='Mark selected applications as Selected')
    def mark_as_selected(self, request, queryset):
        _bulk_update_status(self, request, queryset, JobApplication.STATUS_SELECTED, 'Selected')


@admin.register(SavedJob)
class SavedJobAdmin(admin.ModelAdmin):
    list_display = ('user', 'job', 'saved_at')
    list_filter = ('saved_at',)
    search_fields = ('user__email', 'user__profile__full_name', 'job__title', 'job__company')
    list_select_related = ('user', 'user__profile', 'job')

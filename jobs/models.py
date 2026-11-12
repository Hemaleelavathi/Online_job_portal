import os

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import Count
from django.utils import timezone

_ACCENT_PALETTE = (
    '#2563eb',
    '#0d9488',
    '#7c3aed',
    '#dc2626',
    '#ea580c',
    '#0284c7',
)


class Job(models.Model):
    """Represents a job listing available on CareerConnect."""

    JOB_TYPE_FULL_TIME = 'Full-Time'
    JOB_TYPE_PART_TIME = 'Part-Time'
    JOB_TYPE_REMOTE = 'Remote'
    JOB_TYPE_HYBRID = 'Hybrid'
    JOB_TYPE_CONTRACT = 'Contract'
    JOB_TYPE_CHOICES = [
        (JOB_TYPE_FULL_TIME, 'Full-Time'),
        (JOB_TYPE_PART_TIME, 'Part-Time'),
        (JOB_TYPE_REMOTE, 'Remote'),
        (JOB_TYPE_HYBRID, 'Hybrid'),
        (JOB_TYPE_CONTRACT, 'Contract'),
    ]

    title = models.CharField(max_length=150)
    company = models.CharField(max_length=150)
    location = models.CharField(max_length=120)
    job_type = models.CharField(max_length=30, choices=JOB_TYPE_CHOICES, default=JOB_TYPE_FULL_TIME)
    salary = models.CharField(max_length=80, blank=True)
    skills_required = models.CharField(max_length=250, blank=True)
    experience = models.CharField(max_length=80, blank=True)
    description = models.TextField()
    employer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='posted_jobs',
    )
    is_active = models.BooleanField(default=True)
    posted_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-posted_date', 'id']

    @property
    def initials(self):
        """Return up to two uppercase initials for the company avatar."""
        words = self.company.split()
        if len(words) >= 2:
            return (words[0][0] + words[1][0]).upper()
        return self.company[:2].upper()

    @property
    def accent_color(self):
        """Return a consistent accent color hex code derived from the company name."""
        index = sum(ord(ch) for ch in self.company) % len(_ACCENT_PALETTE)
        return _ACCENT_PALETTE[index]

    @property
    def skill_list(self):
        """Return a cleaned list of required skills."""
        return [item.strip() for item in self.skills_required.split(',') if item.strip()]

    def __str__(self):
        return f'{self.title} at {self.company}'


class JobApplication(models.Model):
    """Tracks a Job Seeker's application to a specific Job listing."""

    STATUS_APPLIED = 'applied'
    STATUS_SHORTLISTED = 'shortlisted'
    STATUS_REJECTED = 'rejected'
    STATUS_SELECTED = 'selected'
    STATUS_CHOICES = [
        (STATUS_APPLIED, 'Applied'),
        (STATUS_SHORTLISTED, 'Shortlisted'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_SELECTED, 'Selected'),
    ]
    STATUS_BADGE_CLASSES = {
        STATUS_APPLIED: 'bg-primary-subtle text-primary',
        STATUS_SHORTLISTED: 'bg-warning-subtle text-warning-emphasis',
        STATUS_REJECTED: 'bg-danger-subtle text-danger',
        STATUS_SELECTED: 'bg-success-subtle text-success',
    }

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name='applications',
    )
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='job_applications',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_APPLIED)
    resume = models.FileField(
        upload_to='application_resumes/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
    )
    cover_note = models.TextField(blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    status_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-applied_at', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['job', 'applicant'],
                name='unique_job_application',
            ),
        ]

    @property
    def effective_resume(self):
        """Return the application-specific resume if uploaded, else the applicant's profile resume."""
        if self.resume:
            return self.resume
        profile = getattr(self.applicant, 'profile', None)
        return profile.resume if profile and profile.resume else None

    @property
    def resume_filename(self):
        """Return the filename of the effective resume attached to this application."""
        resume_file = self.effective_resume
        return os.path.basename(resume_file.name) if resume_file else ''

    @property
    def status_badge_class(self):
        """Return Bootstrap badge utility classes matching this application's status."""
        return self.STATUS_BADGE_CLASSES.get(self.status, 'bg-secondary-subtle text-secondary')

    @classmethod
    def status_summary(cls, queryset):
        """Return ordered counts per application status for a given JobApplication queryset."""
        raw_counts = queryset.order_by().values('status').annotate(total=Count('id'))
        counts = {row['status']: row['total'] for row in raw_counts}
        return [
            {
                'value': code,
                'label': label,
                'count': counts.get(code, 0),
                'badge_class': cls.STATUS_BADGE_CLASSES.get(code, 'bg-secondary-subtle text-secondary'),
            }
            for code, label in cls.STATUS_CHOICES
        ]

    @classmethod
    def filter_by_status(cls, queryset, raw_status):
        """Return (filtered_queryset, selected_status, is_valid) for a status filter string."""
        selected_status = (raw_status or '').strip()
        if not selected_status:
            return queryset, '', True
        valid_statuses = {code for code, _ in cls.STATUS_CHOICES}
        if selected_status not in valid_statuses:
            return queryset, selected_status, False
        return queryset.filter(status=selected_status), selected_status, True

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and not self.status_history.exists():
            ApplicationStatusHistory.objects.create(
                application=self,
                status=self.status,
                changed_by=self.applicant,
            )

    def update_status(self, new_status, changed_by=None):
        """Update application status and append a status history record when changed."""
        valid_statuses = {code for code, _ in self.STATUS_CHOICES}
        if new_status not in valid_statuses:
            raise ValueError(f'Invalid application status: {new_status}')
        if self.status == new_status:
            return False
        self.status = new_status
        self.status_updated_at = timezone.now()
        self.save(update_fields=['status', 'status_updated_at'])
        ApplicationStatusHistory.objects.create(
            application=self,
            status=new_status,
            changed_by=changed_by,
        )
        return True

    def __str__(self):
        return f'{self.applicant} -> {self.job} ({self.get_status_display()})'


class ApplicationStatusHistory(models.Model):
    """Stores the chronological status transition history for a JobApplication."""

    application = models.ForeignKey(
        JobApplication,
        on_delete=models.CASCADE,
        related_name='status_history',
    )
    status = models.CharField(max_length=20, choices=JobApplication.STATUS_CHOICES)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='application_status_changes',
    )
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['changed_at', 'id']

    @property
    def status_badge_class(self):
        """Return Bootstrap badge utility classes matching this historical status."""
        return JobApplication.STATUS_BADGE_CLASSES.get(
            self.status,
            'bg-secondary-subtle text-secondary',
        )

    def __str__(self):
        return f'{self.application_id}: {self.get_status_display()}'


class SavedJob(models.Model):
    """Bookmarks a Job listing saved by a user to revisit or apply later."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_jobs',
    )
    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name='saved_by',
    )
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-saved_at', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'job'],
                name='unique_saved_job',
            ),
        ]

    def __str__(self):
        return f'{self.user} saved {self.job}'

import os

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models


class UserProfile(models.Model):
    """Stores portal role, contact details, qualifications, skills, and resume for a user."""

    ROLE_JOB_SEEKER = 'job_seeker'
    ROLE_EMPLOYER = 'employer'
    ROLE_CHOICES = [
        (ROLE_JOB_SEEKER, 'Job Seeker'),
        (ROLE_EMPLOYER, 'Employer'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    full_name = models.CharField(max_length=150)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    phone = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=120, blank=True)
    company_name = models.CharField(max_length=150, blank=True)
    company_description = models.TextField(blank=True)
    qualification = models.CharField(max_length=150, blank=True)
    skills = models.CharField(max_length=300, blank=True)
    resume = models.FileField(
        upload_to='resumes/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def skill_list(self):
        """Return a cleaned list of individual skills parsed from the comma-separated field."""
        return [item.strip() for item in self.skills.split(',') if item.strip()]

    @property
    def resume_filename(self):
        """Return just the filename of the uploaded resume without its directory prefix."""
        return os.path.basename(self.resume.name) if self.resume else ''

    def __str__(self):
        return f'{self.full_name} ({self.get_role_display()})'

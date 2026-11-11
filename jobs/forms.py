from django import forms
from django.core.exceptions import ValidationError

from accounts.validators import validate_pdf_resume

from .models import Job, JobApplication


def _clean_text_field(value, field_label, min_length=2):
    """Collapse extra whitespace and enforce a minimum character length."""
    cleaned = ' '.join((value or '').split())
    if len(cleaned) < min_length:
        raise ValidationError(
            f'Please enter a valid {field_label.lower()} (at least {min_length} characters).'
        )
    return cleaned


class JobForm(forms.ModelForm):
    """Validates job creation and editing fields for Employers."""

    class Meta:
        model = Job
        fields = (
            'title',
            'company',
            'location',
            'job_type',
            'salary',
            'experience',
            'skills_required',
            'description',
            'is_active',
        )
        labels = {
            'title': 'Job Title',
            'company': 'Company Name',
            'location': 'Location',
            'job_type': 'Job Type',
            'salary': 'Salary',
            'experience': 'Experience',
            'skills_required': 'Required Skills',
            'description': 'Job Description',
            'is_active': 'Publish job immediately (active)',
        }
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Senior Django Backend Engineer',
            }),
            'company': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Acme Technologies',
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Bengaluru, IN or Remote',
            }),
            'job_type': forms.Select(attrs={
                'class': 'form-select',
            }),
            'salary': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. $85k - $110k',
            }),
            'experience': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 2-4 years or Fresher',
            }),
            'skills_required': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Python, Django, PostgreSQL, REST API',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Describe key responsibilities, requirements, and benefits...',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }
        help_texts = {
            'skills_required': 'Separate multiple skills with commas.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for required_field in ('salary', 'experience', 'skills_required'):
            self.fields[required_field].required = True

    def clean_title(self):
        return _clean_text_field(self.cleaned_data.get('title'), 'job title')

    def clean_company(self):
        return _clean_text_field(self.cleaned_data.get('company'), 'company name')

    def clean_location(self):
        return _clean_text_field(self.cleaned_data.get('location'), 'job location')

    def clean_salary(self):
        return _clean_text_field(self.cleaned_data.get('salary'), 'salary range')

    def clean_experience(self):
        return _clean_text_field(self.cleaned_data.get('experience'), 'experience requirement')

    def clean_skills_required(self):
        raw = self.cleaned_data.get('skills_required', '')
        skills = [item.strip() for item in raw.split(',') if item.strip()]
        if not skills:
            raise ValidationError('Please list at least one required skill.')
        return ', '.join(skills)

    def clean_description(self):
        description = (self.cleaned_data.get('description') or '').strip()
        if len(description) < 10:
            raise ValidationError('Please enter a job description (at least 10 characters).')
        return description


class JobApplicationForm(forms.ModelForm):
    """Validates optional PDF resume upload and cover note when applying to a job."""

    class Meta:
        model = JobApplication
        fields = ('resume', 'cover_note')
        labels = {
            'resume': 'Upload Resume (PDF)',
            'cover_note': 'Cover Note (Optional)',
        }
        widgets = {
            'resume': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,application/pdf',
            }),
            'cover_note': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Briefly share why you are a great fit for this role (optional)...',
            }),
        }
        help_texts = {
            'resume': 'Upload a PDF resume (max 5 MB), or leave empty to use your profile resume.',
        }

    def clean_resume(self):
        return validate_pdf_resume(self.cleaned_data.get('resume'))

    def clean_cover_note(self):
        return (self.cleaned_data.get('cover_note') or '').strip()


class ApplicationStatusForm(forms.ModelForm):
    """Validates Employer status updates for a candidate JobApplication."""

    class Meta:
        model = JobApplication
        fields = ('status',)
        labels = {
            'status': 'Application Status',
        }
        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-select form-select-sm',
            }),
        }

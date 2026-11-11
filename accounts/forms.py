from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from .models import UserProfile
from .validators import validate_pdf_resume

User = get_user_model()


def _normalize_full_name(value):
    """Collapse extra whitespace and validate minimum length for a user's full name."""
    full_name = ' '.join((value or '').split())
    if len(full_name) < 2:
        raise ValidationError('Please enter your full name (at least 2 characters).')
    return full_name


def _split_full_name(full_name):
    """Split a full name into first_name and last_name values."""
    parts = full_name.split(None, 1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else ''
    return first_name, last_name


class RegistrationForm(forms.Form):
    """Validates user registration details and creates a User with a UserProfile."""

    full_name = forms.CharField(
        label='Full Name',
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your full name',
            'autocomplete': 'name',
        }),
    )
    email = forms.EmailField(
        label='Email Address',
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'you@example.com',
            'autocomplete': 'email',
        }),
    )
    role = forms.ChoiceField(
        label='User Role',
        choices=[('', 'Select your role'), *UserProfile.ROLE_CHOICES],
        widget=forms.Select(attrs={
            'class': 'form-select',
        }),
    )
    password = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Create a strong password',
            'autocomplete': 'new-password',
        }),
        help_text='Use at least 8 characters and avoid common or all-numeric passwords.',
    )
    confirm_password = forms.CharField(
        label='Confirm Password',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Re-enter your password',
            'autocomplete': 'new-password',
        }),
    )

    def clean_full_name(self):
        return _normalize_full_name(self.cleaned_data.get('full_name'))

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(Q(email__iexact=email) | Q(username__iexact=email)).exists():
            raise ValidationError('An account with this email address already exists.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', 'Passwords do not match.')

        if password:
            full_name = cleaned_data.get('full_name', '')
            email = cleaned_data.get('email', '')
            first_name, last_name = _split_full_name(full_name) if full_name else ('', '')
            candidate = User(
                username=email,
                email=email,
                first_name=first_name,
                last_name=last_name,
            )
            try:
                validate_password(password, user=candidate)
            except ValidationError as exc:
                self.add_error('password', exc)

        return cleaned_data

    def save(self):
        """Create and persist the authenticated Django User and linked UserProfile."""
        full_name = self.cleaned_data['full_name']
        email = self.cleaned_data['email']
        password = self.cleaned_data['password']
        role = self.cleaned_data['role']
        first_name, last_name = _split_full_name(full_name)

        with transaction.atomic():
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            UserProfile.objects.create(
                user=user,
                full_name=full_name,
                role=role,
            )

        return user


class LoginForm(forms.Form):
    """Authenticates a CareerConnect user by email address and password."""

    email = forms.EmailField(
        label='Email Address',
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'you@example.com',
            'autocomplete': 'email',
        }),
    )
    password = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password',
        }),
    )

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean_email(self):
        return self.cleaned_data.get('email', '').strip().lower()

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if email and password:
            matched_user = User.objects.filter(
                Q(email__iexact=email) | Q(username__iexact=email)
            ).order_by('id').first()
            lookup_username = matched_user.username if matched_user else email

            self.user_cache = authenticate(
                self.request,
                username=lookup_username,
                password=password,
            )
            if self.user_cache is None:
                raise ValidationError(
                    'Invalid email address or password.',
                    code='invalid_login',
                )

        return cleaned_data

    def get_user(self):
        return self.user_cache


class JobSeekerProfileForm(forms.ModelForm):
    """Validates and saves Job Seeker profile fields including skills, qualification, and PDF resume."""

    class Meta:
        model = UserProfile
        fields = ('full_name', 'phone', 'location', 'qualification', 'skills', 'resume')
        labels = {
            'full_name': 'Full Name',
            'phone': 'Phone Number',
            'location': 'Location',
            'qualification': 'Highest Qualification',
            'skills': 'Skills',
            'resume': 'Resume (PDF only)',
        }
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your full name',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. +91 98765 43210',
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Bengaluru, IN or Remote',
            }),
            'qualification': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. B.Tech in Computer Science',
            }),
            'skills': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Python, Django, SQL, Bootstrap 5',
            }),
            'resume': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,application/pdf',
            }),
        }
        help_texts = {
            'skills': 'Separate multiple skills with commas.',
            'resume': 'Upload a PDF document up to 5 MB.',
        }

    def clean_full_name(self):
        return _normalize_full_name(self.cleaned_data.get('full_name'))

    def clean_phone(self):
        return self.cleaned_data.get('phone', '').strip()

    def clean_location(self):
        return self.cleaned_data.get('location', '').strip()

    def clean_qualification(self):
        return self.cleaned_data.get('qualification', '').strip()

    def clean_skills(self):
        raw_skills = self.cleaned_data.get('skills', '')
        return ', '.join([item.strip() for item in raw_skills.split(',') if item.strip()])

    def clean_resume(self):
        return validate_pdf_resume(self.cleaned_data.get('resume'))

    def save(self, commit=True):
        profile = super().save(commit=False)
        return _save_profile_with_user_name(profile, commit=commit)


def _save_profile_with_user_name(profile, commit=True):
    """Persist a UserProfile and keep the linked User first/last name synchronized."""
    first_name, last_name = _split_full_name(profile.full_name)
    if commit:
        with transaction.atomic():
            profile.save()
            user = profile.user
            user.first_name = first_name
            user.last_name = last_name
            user.save(update_fields=['first_name', 'last_name'])
    return profile


class EmployerProfileForm(forms.ModelForm):
    """Validates and saves Employer contact and company details."""

    class Meta:
        model = UserProfile
        fields = ('full_name', 'company_name', 'company_description', 'location', 'phone')
        labels = {
            'full_name': 'Employer Name',
            'company_name': 'Company Name',
            'company_description': 'Company Description',
            'location': 'Headquarters / Location',
            'phone': 'Contact Phone',
        }
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your full name',
            }),
            'company_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Acme Technologies',
            }),
            'company_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe your company culture, mission, and what you build...',
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Bengaluru, IN or Remote',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. +91 98765 43210',
            }),
        }

    def clean_full_name(self):
        return _normalize_full_name(self.cleaned_data.get('full_name'))

    def clean_company_name(self):
        company_name = ' '.join(self.cleaned_data.get('company_name', '').split())
        if len(company_name) < 2:
            raise ValidationError('Please enter your company name (at least 2 characters).')
        return company_name

    def clean_company_description(self):
        return self.cleaned_data.get('company_description', '').strip()

    def clean_location(self):
        return self.cleaned_data.get('location', '').strip()

    def clean_phone(self):
        return self.cleaned_data.get('phone', '').strip()

    def save(self, commit=True):
        profile = super().save(commit=False)
        return _save_profile_with_user_name(profile, commit=commit)

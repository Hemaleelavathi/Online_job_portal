from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import UserProfile

ROLE_DASHBOARD_URLS = {
    UserProfile.ROLE_JOB_SEEKER: 'job_seeker_dashboard',
    UserProfile.ROLE_EMPLOYER: 'employer_dashboard',
}


def get_dashboard_url_name(user):
    """Return the role-specific dashboard URL name for a user, or 'home' as fallback."""
    if getattr(user, 'is_staff', False):
        return 'admin_dashboard'
    profile = getattr(user, 'profile', None)
    if profile and profile.role in ROLE_DASHBOARD_URLS:
        return ROLE_DASHBOARD_URLS[profile.role]
    return 'home'


def render_access_denied(request, required_role):
    """Return a consistent HTTP 403 access denied page for unauthorized actions."""
    return render(
        request,
        'accounts/access_denied.html',
        {
            'required_role': required_role,
            'dashboard_url_name': get_dashboard_url_name(request.user),
        },
        status=403,
    )


def role_required(expected_role):
    """Protect a view so only authenticated users with the matching role can access it."""

    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            profile = getattr(request.user, 'profile', None)
            if profile is None or profile.role != expected_role:
                return render_access_denied(
                    request,
                    dict(UserProfile.ROLE_CHOICES).get(expected_role, ''),
                )
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


def staff_required(view_func):
    """Protect a view so only authenticated admin/staff users can access it."""

    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            return render_access_denied(request, 'Admin / Staff')
        return view_func(request, *args, **kwargs)

    return _wrapped

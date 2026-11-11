from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'user', 'role', 'company_name', 'qualification', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('full_name', 'user__email', 'user__username', 'company_name', 'skills', 'qualification')

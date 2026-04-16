from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AuthSecurityLog, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("扩展信息", {"fields": ("name", "phone", "education", "skills", "experience")}),
    )


@admin.register(AuthSecurityLog)
class AuthSecurityLogAdmin(admin.ModelAdmin):
    list_display = ("id", "event_type", "username", "client_ip", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("username", "client_ip")
    ordering = ("-created_at", "-id")

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    name = models.CharField(max_length=50, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    education = models.CharField(max_length=100, blank=True, null=True)
    skills = models.TextField(blank=True, null=True)
    experience = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.username


class AuthSecurityLog(models.Model):
    EVENT_LOGIN_FAILED = "LOGIN_FAILED"
    EVENT_LOGIN_LOCK_TRIGGERED = "LOGIN_LOCK_TRIGGERED"
    EVENT_LOGIN_LOCK_BLOCKED = "LOGIN_LOCK_BLOCKED"
    EVENT_LOGIN_SUCCESS = "LOGIN_SUCCESS"
    EVENT_LOGIN_FAILURES_RESET = "LOGIN_FAILURES_RESET"

    EVENT_CHOICES = (
        (EVENT_LOGIN_FAILED, "登录失败"),
        (EVENT_LOGIN_LOCK_TRIGGERED, "触发封禁"),
        (EVENT_LOGIN_LOCK_BLOCKED, "封禁中拦截"),
        (EVENT_LOGIN_SUCCESS, "登录成功"),
        (EVENT_LOGIN_FAILURES_RESET, "失败计数重置"),
    )

    user = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="auth_security_logs",
    )
    username = models.CharField(max_length=150, blank=True, default="")
    client_ip = models.GenericIPAddressField(null=True, blank=True)
    event_type = models.CharField(max_length=64, choices=EVENT_CHOICES, db_index=True)
    detail = models.JSONField(blank=True, default=dict)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "auth_security_logs"
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(fields=["username", "-created_at"]),
            models.Index(fields=["client_ip", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.event_type}({self.username}@{self.client_ip})"

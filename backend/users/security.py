"""Security helpers for login failure tracking and temporary lockout."""

import ipaddress

from django.conf import settings
from django.core.cache import cache

from .models import AuthSecurityLog


def _normalize_username(username):
    return str(username or "").strip().lower()


def _normalize_ip(client_ip):
    return str(client_ip or "").strip() or "unknown"


def _ip_for_log(client_ip):
    raw = str(client_ip or "").strip()
    if not raw:
        return None
    try:
        return str(ipaddress.ip_address(raw))
    except ValueError:
        return None


def _lock_key_username(username):
    return f"auth:login:lock:user:{_normalize_username(username)}"


def _lock_key_ip(client_ip):
    return f"auth:login:lock:ip:{_normalize_ip(client_ip)}"


def _fail_key_username(username):
    return f"auth:login:fail:user:{_normalize_username(username)}"


def _fail_key_ip(client_ip):
    return f"auth:login:fail:ip:{_normalize_ip(client_ip)}"


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        # Prefer the left-most client IP when behind proxy chain.
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "") or "unknown"


def create_security_log(event_type, username="", client_ip="", detail=None, user=None):
    try:
        AuthSecurityLog.objects.create(
            user=user,
            username=_normalize_username(username),
            client_ip=_ip_for_log(client_ip),
            event_type=event_type,
            detail=detail or {},
        )
    except Exception:
        # Security log persistence should never block auth flow.
        return


def get_login_lock_status(username, client_ip):
    lock_seconds = int(getattr(settings, "AUTH_LOGIN_LOCK_SECONDS", 600))
    user_ttl = cache.ttl(_lock_key_username(username)) if hasattr(cache, "ttl") else None
    ip_ttl = cache.ttl(_lock_key_ip(client_ip)) if hasattr(cache, "ttl") else None

    user_locked = bool(cache.get(_lock_key_username(username)))
    ip_locked = bool(cache.get(_lock_key_ip(client_ip)))
    if not user_locked and not ip_locked:
        return {"locked": False, "retry_after": 0}

    retry_after_candidates = []
    if user_locked:
        retry_after_candidates.append(user_ttl if isinstance(user_ttl, int) and user_ttl > 0 else lock_seconds)
    if ip_locked:
        retry_after_candidates.append(ip_ttl if isinstance(ip_ttl, int) and ip_ttl > 0 else lock_seconds)
    retry_after = max(retry_after_candidates) if retry_after_candidates else lock_seconds
    return {"locked": True, "retry_after": max(1, int(retry_after))}


def clear_login_failures(username):
    user_fail_key = _fail_key_username(username)
    user_lock_key = _lock_key_username(username)
    fail_count = int(cache.get(user_fail_key) or 0)
    had_lock = bool(cache.get(user_lock_key))
    cache.delete_many(
        [
            user_fail_key,
            user_lock_key,
        ]
    )
    return {"had_failures": fail_count > 0, "had_lock": had_lock, "failed_count": fail_count}


def record_login_failure(username, client_ip):
    lock_seconds = int(getattr(settings, "AUTH_LOGIN_LOCK_SECONDS", 600))
    failure_window_seconds = int(getattr(settings, "AUTH_LOGIN_FAILURE_WINDOW_SECONDS", lock_seconds))
    username_limit = int(getattr(settings, "AUTH_LOGIN_FAIL_LIMIT_USERNAME", 5))
    ip_limit = int(getattr(settings, "AUTH_LOGIN_FAIL_LIMIT_IP", 20))

    user_fail_key = _fail_key_username(username)
    ip_fail_key = _fail_key_ip(client_ip)
    user_lock_key = _lock_key_username(username)
    ip_lock_key = _lock_key_ip(client_ip)

    user_fail_count = int(cache.get(user_fail_key) or 0) + 1
    ip_fail_count = int(cache.get(ip_fail_key) or 0) + 1
    cache.set(user_fail_key, user_fail_count, timeout=failure_window_seconds)
    cache.set(ip_fail_key, ip_fail_count, timeout=failure_window_seconds)

    user_locked = user_fail_count >= username_limit
    ip_locked = ip_fail_count >= ip_limit
    if user_locked:
        cache.set(user_lock_key, 1, timeout=lock_seconds)
    if ip_locked:
        cache.set(ip_lock_key, 1, timeout=lock_seconds)

    if user_locked or ip_locked:
        cache.delete_many([user_fail_key, ip_fail_key])
        return {
            "locked": True,
            "retry_after": max(1, lock_seconds),
            "user_fail_count": user_fail_count,
            "ip_fail_count": ip_fail_count,
            "locked_by": "username" if user_locked else "ip",
        }
    return {
        "locked": False,
        "retry_after": 0,
        "user_fail_count": user_fail_count,
        "ip_fail_count": ip_fail_count,
        "locked_by": "",
    }

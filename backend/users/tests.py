from django.contrib.auth import get_user_model
from django.conf import settings as django_settings
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APITestCase
from datetime import timedelta
from unittest.mock import patch

from .models import AuthSecurityLog

User = get_user_model()


class UserApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.register_payload = {
            "username": "api_user_1",
            "password": "12345678",
            "name": "测试用户",
            "education": "本科",
            "skills": "Python,Django",
            "experience": "3年",
        }

    def test_register_login_profile_and_delete_flow(self):
        register_resp = self.client.post("/api/users/register", self.register_payload, format="json")
        self.assertEqual(register_resp.status_code, 201)
        self.assertTrue(register_resp.data["success"])
        self.assertEqual(register_resp.data["data"]["username"], self.register_payload["username"])

        user = User.objects.get(username=self.register_payload["username"])
        self.assertNotEqual(user.password, self.register_payload["password"])
        self.assertTrue(user.check_password(self.register_payload["password"]))

        dup_resp = self.client.post("/api/users/register", self.register_payload, format="json")
        self.assertEqual(dup_resp.status_code, 400)
        self.assertFalse(dup_resp.data["success"])
        self.assertEqual(dup_resp.data.get("code"), "USER_USERNAME_EXISTS")

        login_resp = self.client.post(
            "/api/users/login",
            {"username": self.register_payload["username"], "password": self.register_payload["password"]},
            format="json",
        )
        self.assertEqual(login_resp.status_code, 200)
        self.assertIn("accessToken", login_resp.data["data"])

        bad_login = self.client.post(
            "/api/users/login",
            {"username": self.register_payload["username"], "password": "wrong-password"},
            format="json",
        )
        self.assertEqual(bad_login.status_code, 401)
        self.assertEqual(bad_login.data.get("code"), "USER_LOGIN_CREDENTIALS_INVALID")

        token = login_resp.data["data"]["accessToken"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        profile_resp = self.client.put(
            "/api/users/profile",
            {"name": "新名字", "skills": "Python,Django,DRF"},
            format="json",
        )
        self.assertEqual(profile_resp.status_code, 200)
        self.assertEqual(profile_resp.data["data"]["name"], "新名字")

        delete_resp = self.client.delete("/api/users/delete")
        self.assertEqual(delete_resp.status_code, 200)
        self.assertFalse(User.objects.filter(username=self.register_payload["username"]).exists())

    def test_profile_requires_auth(self):
        resp = self.client.put("/api/users/profile", {"name": "NoAuth"}, format="json")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.data.get("code"), "COMMON_AUTH_REQUIRED")

    def test_delete_requires_auth_with_error_code(self):
        resp = self.client.delete("/api/users/delete")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.data.get("code"), "USER_DELETE_AUTH_REQUIRED")

    def test_register_invalid_params_contains_error_code(self):
        resp = self.client.post("/api/users/register", {"username": "invalid_only"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data.get("code"), "USER_REGISTER_INVALID_PARAMS")

    def test_login_throttled_returns_common_code(self):
        User.objects.create_user(
            username="throttle_login_user",
            password="12345678",
            name="限流用户",
        )
        throttle_rates = dict(django_settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {}))
        throttle_rates.update({"auth_login": "1/min", "anon": "500/min", "user": "500/min"})
        with patch("rest_framework.throttling.SimpleRateThrottle.THROTTLE_RATES", throttle_rates):
            cache.clear()
            first = self.client.post(
                "/api/users/login",
                {"username": "throttle_login_user", "password": "12345678"},
                format="json",
            )
            second = self.client.post(
                "/api/users/login",
                {"username": "throttle_login_user", "password": "12345678"},
                format="json",
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertEqual(second.data.get("code"), "COMMON_TOO_MANY_REQUESTS")
        self.assertIn("retry_after", second.data.get("data", {}))

    def test_login_temp_lock_after_repeated_failures(self):
        User.objects.create_user(
            username="lock_user",
            password="12345678",
            name="封禁测试用户",
        )
        rest_framework_settings = dict(django_settings.REST_FRAMEWORK)
        throttle_rates = dict(rest_framework_settings.get("DEFAULT_THROTTLE_RATES", {}))
        throttle_rates.update({"auth_login": "500/min", "anon": "500/min", "user": "500/min"})
        rest_framework_settings["DEFAULT_THROTTLE_RATES"] = throttle_rates

        with self.settings(
            REST_FRAMEWORK=rest_framework_settings,
            AUTH_LOGIN_FAIL_LIMIT_USERNAME=2,
            AUTH_LOGIN_FAIL_LIMIT_IP=100,
            AUTH_LOGIN_LOCK_SECONDS=120,
            AUTH_LOGIN_FAILURE_WINDOW_SECONDS=120,
        ):
            with patch("rest_framework.throttling.SimpleRateThrottle.THROTTLE_RATES", throttle_rates):
                cache.clear()
                first_fail = self.client.post(
                    "/api/users/login",
                    {"username": "lock_user", "password": "wrong-password"},
                    format="json",
                )
                second_fail = self.client.post(
                    "/api/users/login",
                    {"username": "lock_user", "password": "wrong-password"},
                    format="json",
                )
                locked_with_right_password = self.client.post(
                    "/api/users/login",
                    {"username": "lock_user", "password": "12345678"},
                    format="json",
                )

        self.assertEqual(first_fail.status_code, 401)
        self.assertEqual(first_fail.data.get("code"), "USER_LOGIN_CREDENTIALS_INVALID")
        self.assertEqual(second_fail.status_code, 429)
        self.assertEqual(second_fail.data.get("code"), "USER_LOGIN_TEMP_LOCKED")
        self.assertIn("retry_after", second_fail.data.get("data", {}))
        self.assertEqual(locked_with_right_password.status_code, 429)
        self.assertEqual(locked_with_right_password.data.get("code"), "USER_LOGIN_TEMP_LOCKED")
        event_types = list(
            AuthSecurityLog.objects.filter(username="lock_user")
            .order_by("id")
            .values_list("event_type", flat=True)
        )
        self.assertEqual(
            event_types,
            [
                AuthSecurityLog.EVENT_LOGIN_FAILED,
                AuthSecurityLog.EVENT_LOGIN_LOCK_TRIGGERED,
                AuthSecurityLog.EVENT_LOGIN_LOCK_BLOCKED,
            ],
        )

    def test_security_logs_requires_auth(self):
        resp = self.client.get("/api/users/security-logs")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.data.get("code"), "COMMON_AUTH_REQUIRED")

    def test_security_logs_query_by_username_and_ip(self):
        viewer = User.objects.create_user(username="log_viewer", password="12345678")
        AuthSecurityLog.objects.create(
            username="alice",
            client_ip="127.0.0.1",
            event_type=AuthSecurityLog.EVENT_LOGIN_FAILED,
            detail={"user_fail_count": 1},
        )
        AuthSecurityLog.objects.create(
            username="alice",
            client_ip="10.0.0.8",
            event_type=AuthSecurityLog.EVENT_LOGIN_SUCCESS,
            detail={},
        )
        AuthSecurityLog.objects.create(
            username="bob",
            client_ip="127.0.0.1",
            event_type=AuthSecurityLog.EVENT_LOGIN_LOCK_TRIGGERED,
            detail={"retry_after": 120},
        )

        self.client.force_authenticate(user=viewer)
        by_username = self.client.get("/api/users/security-logs", {"username": "alice"})
        self.assertEqual(by_username.status_code, 200)
        self.assertEqual(by_username.data["data"]["total"], 2)

        by_ip = self.client.get("/api/users/security-logs", {"client_ip": "127.0.0.1"})
        self.assertEqual(by_ip.status_code, 200)
        self.assertEqual(by_ip.data["data"]["total"], 2)
        self.assertTrue(all(item["client_ip"] == "127.0.0.1" for item in by_ip.data["data"]["logs"]))

    def test_security_logs_invalid_pagination_code(self):
        viewer = User.objects.create_user(username="pagination_viewer", password="12345678")
        self.client.force_authenticate(user=viewer)
        resp = self.client.get("/api/users/security-logs", {"page": "bad"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data.get("code"), "USER_SECURITY_LOG_PAGE_INVALID")

    def test_security_logs_query_by_time_range(self):
        viewer = User.objects.create_user(username="time_range_viewer", password="12345678")
        base_time = timezone.now()
        old_time = base_time - timedelta(days=3)
        hit_time = base_time - timedelta(days=1)
        recent_time = base_time

        old_log = AuthSecurityLog.objects.create(
            username="alice",
            client_ip="127.0.0.1",
            event_type=AuthSecurityLog.EVENT_LOGIN_FAILED,
            detail={},
        )
        recent_log = AuthSecurityLog.objects.create(
            username="alice",
            client_ip="127.0.0.1",
            event_type=AuthSecurityLog.EVENT_LOGIN_SUCCESS,
            detail={},
        )
        hit_log = AuthSecurityLog.objects.create(
            username="alice",
            client_ip="127.0.0.1",
            event_type=AuthSecurityLog.EVENT_LOGIN_LOCK_BLOCKED,
            detail={},
        )

        AuthSecurityLog.objects.filter(pk=old_log.pk).update(created_at=old_time)
        AuthSecurityLog.objects.filter(pk=hit_log.pk).update(created_at=hit_time)
        AuthSecurityLog.objects.filter(pk=recent_log.pk).update(created_at=recent_time)

        self.client.force_authenticate(user=viewer)
        start_time = (base_time - timedelta(days=2)).isoformat()
        end_time = (base_time + timedelta(hours=1)).isoformat()
        resp = self.client.get("/api/users/security-logs", {"start_time": start_time, "end_time": end_time})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["data"]["total"], 2)
        self.assertTrue(all(item["event_type"] != AuthSecurityLog.EVENT_LOGIN_FAILED for item in resp.data["data"]["logs"]))

    def test_security_logs_invalid_time_filters_return_error_codes(self):
        viewer = User.objects.create_user(username="time_validation_viewer", password="12345678")
        self.client.force_authenticate(user=viewer)

        bad_start = self.client.get("/api/users/security-logs", {"start_time": "not-a-time"})
        self.assertEqual(bad_start.status_code, 400)
        self.assertEqual(bad_start.data.get("code"), "USER_SECURITY_LOG_START_TIME_INVALID")

        bad_end = self.client.get("/api/users/security-logs", {"end_time": "not-a-time"})
        self.assertEqual(bad_end.status_code, 400)
        self.assertEqual(bad_end.data.get("code"), "USER_SECURITY_LOG_END_TIME_INVALID")

        reverse_range = self.client.get(
            "/api/users/security-logs",
            {"start_time": "2026-04-16T10:00:00+08:00", "end_time": "2026-04-15T10:00:00+08:00"},
        )
        self.assertEqual(reverse_range.status_code, 400)
        self.assertEqual(reverse_range.data.get("code"), "USER_SECURITY_LOG_TIME_RANGE_INVALID")

    def test_security_logs_invalid_event_type_code(self):
        viewer = User.objects.create_user(username="event_type_viewer", password="12345678")
        self.client.force_authenticate(user=viewer)
        resp = self.client.get("/api/users/security-logs", {"event_type": "UNKNOWN_EVENT"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data.get("code"), "USER_SECURITY_LOG_EVENT_TYPE_INVALID")

    def test_security_logs_stats_requires_auth(self):
        resp = self.client.get("/api/users/security-logs/stats")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.data.get("code"), "COMMON_AUTH_REQUIRED")

    def test_security_logs_stats_aggregates_with_filters(self):
        viewer = User.objects.create_user(username="stats_viewer", password="12345678")
        base_time = timezone.now()

        first = AuthSecurityLog.objects.create(
            username="alice",
            client_ip="127.0.0.1",
            event_type=AuthSecurityLog.EVENT_LOGIN_FAILED,
            detail={},
        )
        second = AuthSecurityLog.objects.create(
            username="alice",
            client_ip="127.0.0.1",
            event_type=AuthSecurityLog.EVENT_LOGIN_SUCCESS,
            detail={},
        )
        third = AuthSecurityLog.objects.create(
            username="alice",
            client_ip="127.0.0.2",
            event_type=AuthSecurityLog.EVENT_LOGIN_SUCCESS,
            detail={},
        )
        AuthSecurityLog.objects.create(
            username="bob",
            client_ip="10.0.0.8",
            event_type=AuthSecurityLog.EVENT_LOGIN_LOCK_TRIGGERED,
            detail={},
        )

        AuthSecurityLog.objects.filter(pk=first.pk).update(created_at=base_time - timedelta(days=1))
        AuthSecurityLog.objects.filter(pk=second.pk).update(created_at=base_time)
        AuthSecurityLog.objects.filter(pk=third.pk).update(created_at=base_time)

        self.client.force_authenticate(user=viewer)
        resp = self.client.get("/api/users/security-logs/stats", {"username": "alice"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["data"]["total"], 3)

        share = resp.data["data"]["event_share"]
        self.assertEqual(len(share), 2)
        self.assertEqual(share[0]["event_type"], AuthSecurityLog.EVENT_LOGIN_SUCCESS)
        self.assertEqual(share[0]["count"], 2)
        self.assertEqual(share[0]["percentage"], 66.67)
        self.assertEqual(share[1]["event_type"], AuthSecurityLog.EVENT_LOGIN_FAILED)
        self.assertEqual(share[1]["count"], 1)
        self.assertEqual(share[1]["percentage"], 33.33)

        trend = resp.data["data"]["daily_trend"]
        self.assertEqual(len(trend), 2)
        self.assertEqual(trend[0]["count"], 1)
        self.assertEqual(trend[1]["count"], 2)

    def test_security_logs_stats_invalid_time_filters_return_error_codes(self):
        viewer = User.objects.create_user(username="stats_time_validation_viewer", password="12345678")
        self.client.force_authenticate(user=viewer)
        bad_start = self.client.get("/api/users/security-logs/stats", {"start_time": "not-a-time"})
        self.assertEqual(bad_start.status_code, 400)
        self.assertEqual(bad_start.data.get("code"), "USER_SECURITY_LOG_START_TIME_INVALID")

    def test_security_logs_export_csv(self):
        viewer = User.objects.create_user(username="export_viewer", password="12345678")
        AuthSecurityLog.objects.create(
            username="alice",
            client_ip="127.0.0.1",
            event_type=AuthSecurityLog.EVENT_LOGIN_FAILED,
            detail={"user_fail_count": 1},
        )
        AuthSecurityLog.objects.create(
            username="bob",
            client_ip="127.0.0.2",
            event_type=AuthSecurityLog.EVENT_LOGIN_SUCCESS,
            detail={},
        )

        self.client.force_authenticate(user=viewer)
        resp = self.client.get("/api/users/security-logs/export", {"username": "alice"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp["Content-Type"])
        self.assertIn("attachment; filename=", resp["Content-Disposition"])

        csv_text = resp.content.decode("utf-8-sig")
        lines = csv_text.strip().splitlines()
        self.assertGreaterEqual(len(lines), 2)
        self.assertEqual(lines[0], "id,event_type,event_name,username,client_ip,created_at,detail")
        self.assertIn("LOGIN_FAILED", lines[1])
        self.assertNotIn("LOGIN_SUCCESS", csv_text)

    def test_security_logs_export_basic_fields_csv(self):
        viewer = User.objects.create_user(username="export_basic_viewer", password="12345678")
        AuthSecurityLog.objects.create(
            username="alice",
            client_ip="127.0.0.1",
            event_type=AuthSecurityLog.EVENT_LOGIN_FAILED,
            detail={"user_fail_count": 1},
        )

        self.client.force_authenticate(user=viewer)
        resp = self.client.get("/api/users/security-logs/export", {"fields": "basic"})
        self.assertEqual(resp.status_code, 200)

        csv_text = resp.content.decode("utf-8-sig")
        lines = csv_text.strip().splitlines()
        self.assertGreaterEqual(len(lines), 2)
        self.assertEqual(lines[0], "id,event_type,event_name,username,client_ip,created_at")
        self.assertNotIn("detail", lines[0])
        self.assertEqual(len(lines[1].split(",")), 6)

    def test_security_logs_export_invalid_fields_code(self):
        viewer = User.objects.create_user(username="export_invalid_fields_viewer", password="12345678")
        self.client.force_authenticate(user=viewer)
        resp = self.client.get("/api/users/security-logs/export", {"fields": "unknown"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data.get("code"), "USER_SECURITY_LOG_EXPORT_FIELDS_INVALID")

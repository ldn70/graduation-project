from django.test import TestCase
from django.core.cache import cache
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.test import APIRequestFactory, APITestCase
from rest_framework.views import APIView


class _AlwaysDenyPermission(BasePermission):
    def has_permission(self, request, view):
        return False


class _ForbiddenView(APIView):
    authentication_classes = []
    permission_classes = [_AlwaysDenyPermission]

    def get(self, request):
        return Response({"ok": True})


class _RuntimeErrorView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        raise RuntimeError("boom")


class _OnePerMinuteThrottle(SimpleRateThrottle):
    scope = "unit_test"
    rate = "1/min"

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class _ThrottledView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [_OnePerMinuteThrottle]

    def get(self, request):
        return Response({"ok": True})


class GlobalExceptionHandlerTests(APITestCase):
    def setUp(self):
        cache.clear()
        super().setUp()

    def test_not_authenticated_returns_standard_payload(self):
        resp = self.client.put("/api/users/profile", {"name": "NoAuth"}, format="json")
        self.assertEqual(resp.status_code, 401)
        self.assertFalse(resp.data["success"])
        self.assertEqual(resp.data["statusCode"], 401)
        self.assertEqual(resp.data.get("code"), "COMMON_AUTH_REQUIRED")

    def test_not_found_route_returns_standard_payload(self):
        resp = self.client.get("/api/not-found-route")
        self.assertEqual(resp.status_code, 404)

        payload = resp.json()
        self.assertFalse(payload["success"])
        self.assertEqual(payload["statusCode"], 404)
        self.assertEqual(payload.get("code"), "COMMON_RESOURCE_NOT_FOUND")

    def test_permission_denied_returns_standard_payload(self):
        request = APIRequestFactory().get("/api/test/forbidden")
        resp = _ForbiddenView.as_view()(request)

        self.assertEqual(resp.status_code, 403)
        self.assertFalse(resp.data["success"])
        self.assertEqual(resp.data["statusCode"], 403)
        self.assertEqual(resp.data.get("code"), "COMMON_PERMISSION_DENIED")

    def test_unhandled_exception_returns_standard_payload(self):
        request = APIRequestFactory().get("/api/test/runtime-error")
        resp = _RuntimeErrorView.as_view()(request)

        self.assertEqual(resp.status_code, 500)
        self.assertFalse(resp.data["success"])
        self.assertEqual(resp.data["statusCode"], 500)
        self.assertEqual(resp.data.get("code"), "COMMON_INTERNAL_SERVER_ERROR")

    def test_throttled_returns_standard_payload(self):
        view = _ThrottledView.as_view()
        first = view(APIRequestFactory().get("/api/test/throttle"))
        second = view(APIRequestFactory().get("/api/test/throttle"))

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertFalse(second.data["success"])
        self.assertEqual(second.data["statusCode"], 429)
        self.assertEqual(second.data.get("code"), "COMMON_TOO_MANY_REQUESTS")
        self.assertIn("retry_after", second.data.get("data", {}))

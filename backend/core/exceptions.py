"""Global exception handler for Django REST Framework."""

import math

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import exceptions as drf_exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


DEFAULT_MESSAGES = {
    400: "请求参数错误",
    401: "认证失败，请先登录",
    403: "当前账号无权限访问该资源",
    404: "请求的资源不存在",
    405: "请求方法不被允许",
    429: "请求过于频繁，请稍后重试",
    500: "服务器内部错误，请稍后重试",
}

DEFAULT_CODES = {
    400: "COMMON_BAD_REQUEST",
    401: "COMMON_AUTH_REQUIRED",
    403: "COMMON_PERMISSION_DENIED",
    404: "COMMON_RESOURCE_NOT_FOUND",
    405: "COMMON_METHOD_NOT_ALLOWED",
    429: "COMMON_TOO_MANY_REQUESTS",
    500: "COMMON_INTERNAL_SERVER_ERROR",
}

DEFAULT_CODE_MESSAGES = {
    "COMMON_AUTH_REQUIRED": "认证失败，请先登录",
    "COMMON_AUTH_INVALID": "登录凭证无效或已过期",
    "COMMON_PERMISSION_DENIED": "当前账号无权限访问该资源",
    "COMMON_RESOURCE_NOT_FOUND": "请求的资源不存在",
    "COMMON_METHOD_NOT_ALLOWED": "请求方法不被允许",
    "COMMON_TOO_MANY_REQUESTS": "请求过于频繁，请稍后重试",
    "COMMON_INTERNAL_SERVER_ERROR": "服务器内部错误，请稍后重试",
    "COMMON_BAD_REQUEST": "请求参数错误",
}


def _stringify_detail(detail):
    if isinstance(detail, list):
        for item in detail:
            text = _stringify_detail(item)
            if text:
                return text
        return ""
    if isinstance(detail, dict):
        for value in detail.values():
            text = _stringify_detail(value)
            if text:
                return text
        return ""
    if detail is None:
        return ""
    return str(detail)


def _resolve_default_code(exc, status_code):
    if isinstance(exc, drf_exceptions.AuthenticationFailed):
        return "COMMON_AUTH_INVALID"
    if isinstance(exc, drf_exceptions.NotAuthenticated):
        return "COMMON_AUTH_REQUIRED"
    if isinstance(exc, (drf_exceptions.PermissionDenied, DjangoPermissionDenied)):
        return "COMMON_PERMISSION_DENIED"
    if isinstance(exc, (drf_exceptions.NotFound, Http404)):
        return "COMMON_RESOURCE_NOT_FOUND"
    if isinstance(exc, drf_exceptions.Throttled):
        return "COMMON_TOO_MANY_REQUESTS"
    return DEFAULT_CODES.get(status_code)


def api_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        payload = {
            "success": False,
            "message": DEFAULT_MESSAGES[500],
            "data": {},
            "statusCode": 500,
            "code": DEFAULT_CODES[500],
        }
        return Response(payload, status=500)

    status_code = int(response.status_code)
    original_data = response.data

    if isinstance(original_data, dict) and "detail" not in original_data:
        data = original_data
        detail_message = _stringify_detail(original_data)
    else:
        data = {}
        detail_message = _stringify_detail(
            original_data.get("detail") if isinstance(original_data, dict) else original_data
        )

    code = _resolve_default_code(exc, status_code)
    default_message = DEFAULT_MESSAGES.get(status_code, "请求处理失败")
    message = DEFAULT_CODE_MESSAGES.get(code) or detail_message or default_message
    if isinstance(exc, drf_exceptions.Throttled) and exc.wait is not None:
        data = {"retry_after": max(1, int(math.ceil(exc.wait)))}

    payload = {
        "success": False,
        "message": message,
        "data": data if isinstance(data, dict) else {},
        "statusCode": status_code,
    }
    if code:
        payload["code"] = code

    return Response(payload, status=status_code)

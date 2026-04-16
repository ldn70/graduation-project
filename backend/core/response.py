"""Unified API response helpers."""

from rest_framework.response import Response


def success_response(data=None, message="ok", status_code=200):
    return Response(
        {
            "success": True,
            "message": message,
            "data": data if data is not None else {},
            "statusCode": status_code,
        },
        status=status_code,
    )


def error_response(message="error", status_code=400, data=None):
    return Response(
        {
            "success": False,
            "message": message,
            "data": data if data is not None else {},
            "statusCode": status_code,
        },
        status=status_code,
    )

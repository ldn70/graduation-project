"""Global Django HTTP error handlers for non-DRF errors."""

from django.http import JsonResponse


def _error_payload(message, status_code, code):
    return {
        "success": False,
        "message": message,
        "data": {},
        "statusCode": status_code,
        "code": code,
    }


def bad_request_handler(request, exception):
    return JsonResponse(
        _error_payload("请求参数错误", 400, "COMMON_BAD_REQUEST"),
        status=400,
    )


def permission_denied_handler(request, exception):
    return JsonResponse(
        _error_payload("当前账号无权限访问该资源", 403, "COMMON_PERMISSION_DENIED"),
        status=403,
    )


def not_found_handler(request, exception):
    return JsonResponse(
        _error_payload("请求的资源不存在", 404, "COMMON_RESOURCE_NOT_FOUND"),
        status=404,
    )


def server_error_handler(request):
    return JsonResponse(
        _error_payload("服务器内部错误，请稍后重试", 500, "COMMON_INTERNAL_SERVER_ERROR"),
        status=500,
    )

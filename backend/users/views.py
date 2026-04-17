"""API views for user management."""

import csv
import json
from datetime import datetime, time, timedelta

from django.contrib.auth import authenticate
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from core.response import error_response, success_response
from .models import AuthSecurityLog
from .security import (
    create_security_log,
    clear_login_failures,
    get_client_ip,
    get_login_lock_status,
    record_login_failure,
)
from .serializers import (
    AuthSecurityLogSerializer,
    LoginSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    UserInfoSerializer,
)

SECURITY_LOG_EXPORT_MAX_ROWS = 5000
SECURITY_LOG_EVENT_TYPES = {choice[0] for choice in AuthSecurityLog.EVENT_CHOICES}
SECURITY_LOG_EXPORT_FIELD_MODES = {"basic", "full"}


def _parse_security_log_datetime(raw_value, *, param_name, error_code, is_end=False):
    raw_value = str(raw_value or "").strip()
    if not raw_value:
        return None, False, None

    parsed = parse_datetime(raw_value)
    parsed_from_date = False
    if parsed is None:
        parsed_date = parse_date(raw_value)
        if parsed_date is None:
            return (
                None,
                False,
                error_response(
                    f"{param_name} 参数格式错误，请使用 ISO8601 日期或日期时间格式",
                    400,
                    code=error_code,
                ),
            )
        parsed_from_date = True
        parsed = datetime.combine(
            parsed_date + timedelta(days=1) if is_end else parsed_date,
            time.min,
        )

    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())

    return parsed, parsed_from_date, None


def _build_security_log_queryset(request):
    username = request.GET.get("username", "").strip().lower()
    client_ip = request.GET.get("client_ip", "").strip()
    event_type = request.GET.get("event_type", "").strip().upper()
    start_time, _, start_error = _parse_security_log_datetime(
        request.GET.get("start_time"),
        param_name="start_time",
        error_code="USER_SECURITY_LOG_START_TIME_INVALID",
        is_end=False,
    )
    if start_error:
        return None, start_error

    end_time, end_from_date_only, end_error = _parse_security_log_datetime(
        request.GET.get("end_time"),
        param_name="end_time",
        error_code="USER_SECURITY_LOG_END_TIME_INVALID",
        is_end=True,
    )
    if end_error:
        return None, end_error

    if event_type and event_type not in SECURITY_LOG_EVENT_TYPES:
        return (
            None,
            error_response(
                "event_type 参数不在支持范围内",
                400,
                code="USER_SECURITY_LOG_EVENT_TYPE_INVALID",
            ),
        )

    if start_time and end_time:
        if end_from_date_only and start_time >= end_time:
            return (
                None,
                error_response(
                    "start_time 不能晚于 end_time",
                    400,
                    code="USER_SECURITY_LOG_TIME_RANGE_INVALID",
                ),
            )
        if not end_from_date_only and start_time > end_time:
            return (
                None,
                error_response(
                    "start_time 不能晚于 end_time",
                    400,
                    code="USER_SECURITY_LOG_TIME_RANGE_INVALID",
                ),
            )

    queryset = AuthSecurityLog.objects.all()
    if username:
        queryset = queryset.filter(username__icontains=username)
    if client_ip:
        queryset = queryset.filter(client_ip=client_ip)
    if event_type:
        queryset = queryset.filter(event_type=event_type)
    if start_time:
        queryset = queryset.filter(created_at__gte=start_time)
    if end_time:
        if end_from_date_only:
            queryset = queryset.filter(created_at__lt=end_time)
        else:
            queryset = queryset.filter(created_at__lte=end_time)
    return queryset, None


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "auth_register"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            username_errors = serializer.errors.get("username") or []
            if any("already exists" in str(msg).lower() or "已存在" in str(msg) for msg in username_errors):
                return error_response("用户名已存在", 400, serializer.errors, code="USER_USERNAME_EXISTS")
            return error_response(
                "注册失败",
                400,
                serializer.errors,
                code="USER_REGISTER_INVALID_PARAMS",
            )

        username = serializer.validated_data["username"]
        if serializer.Meta.model.objects.filter(username=username).exists():
            return error_response("用户名已存在", 400, code="USER_USERNAME_EXISTS")

        user = serializer.save()
        return success_response(UserInfoSerializer(user).data, "注册成功", 201)


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "auth_login"

    def post(self, request):
        client_ip = get_client_ip(request)
        input_username = request.data.get("username", "")
        lock_status = get_login_lock_status(input_username, client_ip)
        if lock_status["locked"]:
            create_security_log(
                AuthSecurityLog.EVENT_LOGIN_LOCK_BLOCKED,
                username=input_username,
                client_ip=client_ip,
                detail={"retry_after": lock_status["retry_after"]},
            )
            return error_response(
                "登录尝试过于频繁，请稍后重试",
                429,
                data={"retry_after": lock_status["retry_after"]},
                code="USER_LOGIN_TEMP_LOCKED",
            )

        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                "登录参数无效",
                400,
                serializer.errors,
                code="USER_LOGIN_INVALID_PARAMS",
            )

        user = authenticate(
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        if not user:
            failure_state = record_login_failure(serializer.validated_data["username"], client_ip)
            if failure_state["locked"]:
                create_security_log(
                    AuthSecurityLog.EVENT_LOGIN_LOCK_TRIGGERED,
                    username=serializer.validated_data["username"],
                    client_ip=client_ip,
                    detail={
                        "retry_after": failure_state["retry_after"],
                        "user_fail_count": failure_state["user_fail_count"],
                        "ip_fail_count": failure_state["ip_fail_count"],
                        "locked_by": failure_state["locked_by"],
                    },
                )
                return error_response(
                    "登录尝试过于频繁，请稍后重试",
                    429,
                    data={"retry_after": failure_state["retry_after"]},
                    code="USER_LOGIN_TEMP_LOCKED",
                )
            create_security_log(
                AuthSecurityLog.EVENT_LOGIN_FAILED,
                username=serializer.validated_data["username"],
                client_ip=client_ip,
                detail={
                    "user_fail_count": failure_state["user_fail_count"],
                    "ip_fail_count": failure_state["ip_fail_count"],
                },
            )
            return error_response("用户名或密码错误", 401, code="USER_LOGIN_CREDENTIALS_INVALID")

        reset_state = clear_login_failures(serializer.validated_data["username"])
        if reset_state["had_failures"] or reset_state["had_lock"]:
            create_security_log(
                AuthSecurityLog.EVENT_LOGIN_FAILURES_RESET,
                username=serializer.validated_data["username"],
                client_ip=client_ip,
                detail={
                    "failed_count": reset_state["failed_count"],
                    "had_lock": reset_state["had_lock"],
                },
                user=user,
            )
        create_security_log(
            AuthSecurityLog.EVENT_LOGIN_SUCCESS,
            username=serializer.validated_data["username"],
            client_ip=client_ip,
            detail={},
            user=user,
        )
        refresh = RefreshToken.for_user(user)
        data = {
            "accessToken": str(refresh.access_token),
            "refreshToken": str(refresh),
            "user": UserInfoSerializer(user).data,
        }
        return success_response(data, "登录成功")


class ProfileView(APIView):
    def put(self, request):
        serializer = ProfileUpdateSerializer(instance=request.user, data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response(
                "资料更新失败",
                400,
                serializer.errors,
                code="USER_PROFILE_INVALID_PARAMS",
            )

        user = serializer.save()
        return success_response(UserInfoSerializer(user).data, "资料更新成功")


class DeleteAccountView(APIView):
    permission_classes = [AllowAny]

    def delete(self, request):
        if not request.user or not request.user.is_authenticated:
            return error_response("请先登录后再注销账户", 401, code="USER_DELETE_AUTH_REQUIRED")
        request.user.delete()
        return success_response({}, "账户注销成功")


class SecurityLogListView(APIView):
    throttle_scope = "auth_security_logs"

    def get(self, request):
        queryset, error = _build_security_log_queryset(request)
        if error:
            return error

        try:
            page = int(request.GET.get("page", 1))
        except (TypeError, ValueError):
            return error_response("page 参数格式错误", 400, code="USER_SECURITY_LOG_PAGE_INVALID")
        try:
            per_page = int(request.GET.get("per_page", 20))
        except (TypeError, ValueError):
            return error_response("per_page 参数格式错误", 400, code="USER_SECURITY_LOG_PER_PAGE_INVALID")

        if page <= 0:
            return error_response("page 必须大于 0", 400, code="USER_SECURITY_LOG_PAGE_INVALID")
        if per_page <= 0:
            return error_response("per_page 必须大于 0", 400, code="USER_SECURITY_LOG_PER_PAGE_INVALID")

        paginator = Paginator(queryset, per_page)
        page_obj = paginator.get_page(page)
        items = AuthSecurityLogSerializer(page_obj.object_list, many=True).data

        return success_response(
            {
                "logs": items,
                "total": paginator.count,
                "pages": paginator.num_pages,
                "current": page_obj.number,
                "per_page": per_page,
            },
            "查询成功",
        )


class SecurityLogExportView(APIView):
    throttle_scope = "auth_security_logs_export"

    def get(self, request):
        queryset, error = _build_security_log_queryset(request)
        if error:
            return error

        fields_mode = str(request.GET.get("fields", "full") or "").strip().lower()
        if fields_mode not in SECURITY_LOG_EXPORT_FIELD_MODES:
            return error_response(
                "fields 参数仅支持 basic 或 full",
                400,
                code="USER_SECURITY_LOG_EXPORT_FIELDS_INVALID",
            )

        include_detail = fields_mode == "full"
        filename = f"auth_security_logs_{fields_mode}_{timezone.localtime().strftime('%Y%m%d_%H%M%S')}.csv"
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response.write("\ufeff")

        writer = csv.writer(response)
        if include_detail:
            writer.writerow(["id", "event_type", "event_name", "username", "client_ip", "created_at", "detail"])
        else:
            writer.writerow(["id", "event_type", "event_name", "username", "client_ip", "created_at"])

        logs = queryset[:SECURITY_LOG_EXPORT_MAX_ROWS]
        for log in logs:
            row = [
                log.id,
                log.event_type,
                log.get_event_type_display(),
                log.username or "",
                log.client_ip or "",
                timezone.localtime(log.created_at).strftime("%Y-%m-%d %H:%M:%S"),
            ]
            if include_detail:
                row.append(json.dumps(log.detail or {}, ensure_ascii=False))
            writer.writerow(row)

        return response


class SecurityLogStatsView(APIView):
    throttle_scope = "auth_security_logs"

    def get(self, request):
        queryset, error = _build_security_log_queryset(request)
        if error:
            return error

        total = queryset.count()
        choice_map = dict(AuthSecurityLog.EVENT_CHOICES)

        event_share_rows = (
            queryset.values("event_type")
            .annotate(count=Count("id"))
            .order_by("-count", "event_type")
        )
        event_share = [
            {
                "event_type": row["event_type"],
                "event_name": choice_map.get(row["event_type"], row["event_type"]),
                "count": row["count"],
                "percentage": round((row["count"] / total * 100), 2) if total else 0,
            }
            for row in event_share_rows
        ]

        tz = timezone.get_current_timezone()
        trend_rows = (
            queryset.annotate(date=TruncDate("created_at", tzinfo=tz))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )
        daily_trend = [
            {
                "date": row["date"].isoformat() if row["date"] else "",
                "count": row["count"],
            }
            for row in trend_rows
        ]

        return success_response(
            {
                "total": total,
                "event_share": event_share,
                "daily_trend": daily_trend,
            },
            "统计成功",
        )

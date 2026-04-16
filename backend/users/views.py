"""API views for user management."""

from django.contrib.auth import authenticate
from django.core.paginator import Paginator
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
        username = request.GET.get("username", "").strip().lower()
        client_ip = request.GET.get("client_ip", "").strip()
        event_type = request.GET.get("event_type", "").strip().upper()
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

        queryset = AuthSecurityLog.objects.all()
        if username:
            queryset = queryset.filter(username__icontains=username)
        if client_ip:
            queryset = queryset.filter(client_ip=client_ip)
        if event_type:
            queryset = queryset.filter(event_type=event_type)

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

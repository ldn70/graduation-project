"""API views for user management."""

from django.contrib.auth import authenticate
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from core.response import error_response, success_response
from .serializers import (
    LoginSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    UserInfoSerializer,
)


class RegisterView(APIView):
    permission_classes = [AllowAny]

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

    def post(self, request):
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
            return error_response("用户名或密码错误", 401, code="USER_LOGIN_CREDENTIALS_INVALID")

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
    def delete(self, request):
        request.user.delete()
        return success_response({}, "账户注销成功")

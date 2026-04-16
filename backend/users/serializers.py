"""Serializers for user management APIs."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import AuthSecurityLog

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ("username", "password", "name", "phone", "education", "skills", "experience")

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class ProfileUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=6)

    class Meta:
        model = User
        fields = ("name", "phone", "education", "skills", "experience", "password")

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class UserInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "name", "phone", "education", "skills", "experience", "created_at", "updated_at")


class AuthSecurityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthSecurityLog
        fields = ("id", "event_type", "username", "client_ip", "detail", "created_at")

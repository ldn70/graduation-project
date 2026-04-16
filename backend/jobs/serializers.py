"""Serializers for job APIs."""

from rest_framework import serializers

from .models import Job


class JobListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = (
            "id",
            "title",
            "company",
            "salary",
            "education",
            "skills_required",
            "location",
            "publish_time",
            "job_url",
        )

from django.db import models
from django.conf import settings


class Job(models.Model):
    title = models.CharField(max_length=100)
    company = models.CharField(max_length=100)
    salary = models.CharField(max_length=50, blank=True, null=True)
    education = models.CharField(max_length=50, blank=True, null=True)
    experience = models.CharField(max_length=50, blank=True, null=True)
    skills_required = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    industry = models.CharField(max_length=50, blank=True, null=True)
    publish_time = models.DateTimeField(blank=True, null=True)
    job_url = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = "jobs"
        ordering = ("-publish_time", "-id")

    def __str__(self):
        return f"{self.title} - {self.company}"


class UserAction(models.Model):
    ACTION_CHOICES = (
        ("click", "click"),
        ("favorite", "favorite"),
        ("view", "view"),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="actions")
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="actions")
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES)
    action_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_actions"


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites")
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="favorited_by")
    favorite_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "favorites"
        unique_together = ("user", "job")


class Recommendation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recommendations")
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="recommendations")
    score = models.FloatField(blank=True, null=True)
    recommend_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "recommendations"

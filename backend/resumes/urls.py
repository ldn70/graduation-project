from django.urls import path

from .views import ResumeGenerateView

urlpatterns = [
    path("generate", ResumeGenerateView.as_view(), name="resume-generate"),
]

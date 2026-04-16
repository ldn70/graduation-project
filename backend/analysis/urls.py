from django.urls import path

from .views import (
    JobTrendView,
    RecommendJobsView,
    SalaryPredictView,
    SkillDemandView,
    SkillMatchView,
)

urlpatterns = [
    path("recommend/jobs", RecommendJobsView.as_view(), name="recommend-jobs"),
    path("skills/demand", SkillDemandView.as_view(), name="skills-demand"),
    path("skills/match", SkillMatchView.as_view(), name="skills-match"),
    path("salary/predict", SalaryPredictView.as_view(), name="salary-predict"),
    path("trends/jobs", JobTrendView.as_view(), name="trends-jobs"),
]

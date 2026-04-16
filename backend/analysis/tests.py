import tempfile
from pathlib import Path
from unittest import skipUnless

from django.test import TestCase

from analysis.recommender import (
    SimpleAction,
    SimpleJob,
    get_hybrid_recommendations,
    save_artifact,
    train_hybrid_artifact,
)
from analysis.salary_model import predict_salary_from_payload, train_and_save_salary_model
from jobs.models import Job, UserAction
from users.models import User

try:
    from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: F401

    SKLEARN_READY = True
except Exception:
    SKLEARN_READY = False

try:
    from xgboost import XGBRegressor  # noqa: F401

    XGB_READY = True
except Exception:
    XGB_READY = False


@skipUnless(SKLEARN_READY, "scikit-learn is not installed")
class RecommenderFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="u_reco",
            password="12345678",
            skills="Python,Django,MySQL",
            education="本科",
            experience="3年",
        )
        self.other_user = User.objects.create_user(
            username="u_other",
            password="12345678",
            skills="Java,Spring",
        )

        self.jobs = [
            Job.objects.create(
                title="Python开发工程师",
                company="A公司",
                skills_required="Python Django MySQL",
                description="后端开发",
                industry="互联网",
            ),
            Job.objects.create(
                title="Java开发工程师",
                company="B公司",
                skills_required="Java Spring",
                description="企业应用开发",
                industry="互联网",
            ),
            Job.objects.create(
                title="数据分析师",
                company="C公司",
                skills_required="Python SQL Pandas",
                description="数据分析",
                industry="数据服务",
            ),
        ]

        UserAction.objects.create(user=self.user, job=self.jobs[0], action_type="click")
        UserAction.objects.create(user=self.other_user, job=self.jobs[1], action_type="click")
        UserAction.objects.create(user=self.other_user, job=self.jobs[2], action_type="favorite")

    def test_train_and_recommend(self):
        simple_jobs = [
            SimpleJob(
                id=j.id,
                title=j.title,
                company=j.company,
                industry=j.industry or "",
                location=j.location or "",
                education=j.education or "",
                experience=j.experience or "",
                skills_required=j.skills_required or "",
                description=j.description or "",
            )
            for j in self.jobs
        ]
        actions = [
            SimpleAction(user_id=a.user_id, job_id=a.job_id, action_type=a.action_type)
            for a in UserAction.objects.all()
        ]
        artifact = train_hybrid_artifact(simple_jobs, actions)
        self.assertIn("job_ids", artifact)
        self.assertEqual(len(artifact["job_ids"]), 3)

        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "recommender.pkl"
            save_artifact(artifact, model_path)
            recs = get_hybrid_recommendations(self.user, limit=2, model_path=model_path)

        self.assertTrue(recs)
        self.assertLessEqual(len(recs), 2)
        self.assertIn("job_id", recs[0])
        self.assertIn("match_score", recs[0])


@skipUnless(SKLEARN_READY and XGB_READY, "xgboost/scikit-learn is not installed")
class SalaryModelFlowTests(TestCase):
    def setUp(self):
        for i in range(40):
            Job.objects.create(
                title=f"Python开发工程师{i}",
                company=f"公司{i % 5}",
                salary=f"{10 + i % 8}-{15 + i % 8}k",
                education="本科" if i % 2 == 0 else "硕士",
                experience=f"{1 + i % 6}年",
                skills_required="Python Django MySQL" if i % 2 == 0 else "Python Flask PostgreSQL",
                location="上海" if i % 3 == 0 else "北京",
                industry="互联网",
            )

    def test_train_and_predict_salary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "salary_xgb.pkl"
            artifact = train_and_save_salary_model(output_path=model_path, max_jobs=20000)
            self.assertEqual(artifact.get("model_type"), "xgboost")
            self.assertGreater(artifact.get("metrics", {}).get("sample_count", 0), 0)

            result = predict_salary_from_payload(
                {
                    "job_title": "Python开发",
                    "education": "本科",
                    "experience": "3年",
                    "skills": ["Python", "Django", "MySQL"],
                    "city": "上海",
                    "industry": "互联网",
                },
                model_path=model_path,
            )

        self.assertIn("predicted_salary_min", result)
        self.assertIn("predicted_salary_max", result)
        self.assertIn("shap_explanation", result)
        self.assertGreater(result["predicted_salary_max"], result["predicted_salary_min"])

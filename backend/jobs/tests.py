from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import Job
from .utils import parse_experience_years, parse_salary_range_k_month, split_skills


class JobUtilsTests(TestCase):
    def test_split_skills(self):
        skills = split_skills("Python, Django / MySQL；Redis")
        self.assertIn("python", skills)
        self.assertIn("django", skills)
        self.assertIn("mysql", skills)
        self.assertIn("redis", skills)

    def test_parse_experience(self):
        self.assertEqual(parse_experience_years("3-5年"), 4.0)
        self.assertEqual(parse_experience_years("5年"), 5.0)
        self.assertEqual(parse_experience_years("不限"), 0.0)

    def test_parse_salary_range(self):
        self.assertEqual(parse_salary_range_k_month("15-25K"), (15.0, 25.0))
        self.assertEqual(parse_salary_range_k_month("1.5-2万/月"), (15.0, 20.0))
        self.assertEqual(parse_salary_range_k_month("面议"), (None, None))


class JobSearchApiTests(APITestCase):
    def setUp(self):
        now = timezone.now()
        Job.objects.create(
            title="Python开发工程师",
            company="A公司",
            salary="15-25k",
            education="本科",
            skills_required="Python,Django",
            location="上海",
            publish_time=now,
        )
        Job.objects.create(
            title="Java开发工程师",
            company="B公司",
            salary="8-12k",
            education="大专",
            skills_required="Java,Spring",
            location="北京",
            publish_time=now,
        )
        Job.objects.create(
            title="数据分析师",
            company="C公司",
            salary="18-28k",
            education="本科",
            skills_required="Python,SQL",
            location="深圳",
            publish_time=now,
        )

    def test_search_by_keyword_and_pagination(self):
        resp = self.client.get("/api/jobs/search", {"keyword": "Python", "page": 1, "per_page": 1})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["success"])
        self.assertEqual(resp.data["data"]["total"], 2)
        self.assertEqual(len(resp.data["data"]["jobs"]), 1)
        self.assertEqual(resp.data["data"]["current"], 1)

    def test_search_by_salary_filter(self):
        resp = self.client.get("/api/jobs/search", {"salary_min": 16, "salary_max": 30})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["data"]["total"], 2)
        titles = {item["title"] for item in resp.data["data"]["jobs"]}
        self.assertIn("Python开发工程师", titles)
        self.assertIn("数据分析师", titles)

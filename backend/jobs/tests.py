from django.test import TestCase

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

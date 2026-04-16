import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

User = get_user_model()


class ResumeApiTests(APITestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings_ctx = self.settings(MEDIA_ROOT=self.temp_dir.name)
        self.settings_ctx.__enter__()
        self.user = User.objects.create_user(
            username="resume_user",
            password="12345678",
            name="简历用户",
            education="本科",
            skills="Python,Django,MySQL",
            experience="3年",
        )

    def tearDown(self):
        self.settings_ctx.__exit__(None, None, None)
        self.temp_dir.cleanup()
        super().tearDown()

    def test_generate_resume_requires_auth(self):
        resp = self.client.post("/api/resume/generate", {"format": "txt"}, format="json")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.data.get("code"), "COMMON_AUTH_REQUIRED")

    def test_generate_and_download_resume(self):
        self.client.force_authenticate(user=self.user)
        gen_resp = self.client.post("/api/resume/generate", {"format": "txt"}, format="json")
        self.assertEqual(gen_resp.status_code, 200)
        self.assertTrue(gen_resp.data["success"])

        file_url = gen_resp.data["data"]["file_url"]
        filename = file_url.split("/")[-1]
        file_path = Path(self.temp_dir.name) / "resumes" / filename
        self.assertTrue(file_path.exists())

        download_resp = self.client.get(file_url)
        self.assertEqual(download_resp.status_code, 200)
        content = b"".join(download_resp.streaming_content)
        self.assertIn("简历用户".encode("utf-8"), content)

    def test_generate_resume_pdf_fallback_to_txt_file(self):
        self.client.force_authenticate(user=self.user)
        gen_resp = self.client.post("/api/resume/generate", {"format": "pdf"}, format="json")
        self.assertEqual(gen_resp.status_code, 200)
        self.assertEqual(gen_resp.data["data"]["format"], "pdf")
        self.assertTrue(gen_resp.data["data"]["file_url"].endswith(".txt"))

    def test_generate_resume_rejects_unsupported_format_with_code(self):
        self.client.force_authenticate(user=self.user)
        gen_resp = self.client.post("/api/resume/generate", {"format": "docx"}, format="json")
        self.assertEqual(gen_resp.status_code, 400)
        self.assertEqual(gen_resp.data.get("code"), "RESUME_FORMAT_UNSUPPORTED")

    def test_download_missing_file_returns_code(self):
        resp = self.client.get("/download/not-exists-resume.txt")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.data.get("code"), "RESUME_FILE_NOT_FOUND")

    def test_download_read_error_returns_code(self):
        self.client.force_authenticate(user=self.user)
        gen_resp = self.client.post("/api/resume/generate", {"format": "txt"}, format="json")
        file_url = gen_resp.data["data"]["file_url"]

        with patch("resumes.views.open", side_effect=OSError("read failed")):
            resp = self.client.get(file_url)
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.data.get("code"), "RESUME_FILE_READ_FAILED")

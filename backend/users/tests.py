from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

User = get_user_model()


class UserApiTests(APITestCase):
    def setUp(self):
        self.register_payload = {
            "username": "api_user_1",
            "password": "12345678",
            "name": "测试用户",
            "education": "本科",
            "skills": "Python,Django",
            "experience": "3年",
        }

    def test_register_login_profile_and_delete_flow(self):
        register_resp = self.client.post("/api/users/register", self.register_payload, format="json")
        self.assertEqual(register_resp.status_code, 201)
        self.assertTrue(register_resp.data["success"])
        self.assertEqual(register_resp.data["data"]["username"], self.register_payload["username"])

        user = User.objects.get(username=self.register_payload["username"])
        self.assertNotEqual(user.password, self.register_payload["password"])
        self.assertTrue(user.check_password(self.register_payload["password"]))

        dup_resp = self.client.post("/api/users/register", self.register_payload, format="json")
        self.assertEqual(dup_resp.status_code, 400)
        self.assertFalse(dup_resp.data["success"])
        self.assertEqual(dup_resp.data.get("code"), "USER_USERNAME_EXISTS")

        login_resp = self.client.post(
            "/api/users/login",
            {"username": self.register_payload["username"], "password": self.register_payload["password"]},
            format="json",
        )
        self.assertEqual(login_resp.status_code, 200)
        self.assertIn("accessToken", login_resp.data["data"])

        bad_login = self.client.post(
            "/api/users/login",
            {"username": self.register_payload["username"], "password": "wrong-password"},
            format="json",
        )
        self.assertEqual(bad_login.status_code, 401)
        self.assertEqual(bad_login.data.get("code"), "USER_LOGIN_CREDENTIALS_INVALID")

        token = login_resp.data["data"]["accessToken"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        profile_resp = self.client.put(
            "/api/users/profile",
            {"name": "新名字", "skills": "Python,Django,DRF"},
            format="json",
        )
        self.assertEqual(profile_resp.status_code, 200)
        self.assertEqual(profile_resp.data["data"]["name"], "新名字")

        delete_resp = self.client.delete("/api/users/delete")
        self.assertEqual(delete_resp.status_code, 200)
        self.assertFalse(User.objects.filter(username=self.register_payload["username"]).exists())

    def test_profile_requires_auth(self):
        resp = self.client.put("/api/users/profile", {"name": "NoAuth"}, format="json")
        self.assertEqual(resp.status_code, 401)

    def test_delete_requires_auth_with_error_code(self):
        resp = self.client.delete("/api/users/delete")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.data.get("code"), "USER_DELETE_AUTH_REQUIRED")

    def test_register_invalid_params_contains_error_code(self):
        resp = self.client.post("/api/users/register", {"username": "invalid_only"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data.get("code"), "USER_REGISTER_INVALID_PARAMS")

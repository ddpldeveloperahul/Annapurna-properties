from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class AuthenticationTestCase(APITestCase):
    def test_signup(self):
        resp = self.client.post(
            "/api/v1/auth/signup/",
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "Password123",
                "first_name": "New",
                "last_name": "User",
                "phone": "+919876543210",
                "role": "CRM",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertIn("tokens", resp.data)
        self.assertIn("access", resp.data["tokens"])
        self.assertIn("refresh", resp.data["tokens"])
        self.assertEqual(resp.data["user"]["username"], "newuser")
        self.assertEqual(resp.data["user"]["role"], "CRM")

    def test_login(self):
        user = User.objects.create_user(username="loginuser", email="login@example.com", password="Password123")
        
        # Login with email
        resp = self.client.post("/api/v1/auth/login/", {"email": "login@example.com", "password": "Password123"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("tokens", resp.data)
        self.assertIn("access", resp.data["tokens"])
        self.assertIn("refresh", resp.data["tokens"])

        # Login with username in email field
        resp2 = self.client.post("/api/v1/auth/login/", {"email": "loginuser", "password": "Password123"}, format="json")
        self.assertEqual(resp2.status_code, 200)
        self.assertIn("tokens", resp2.data)

    def test_token_refresh(self):
        user = User.objects.create_user(username="refreshuser", password="Password123")
        refresh = RefreshToken.for_user(user)

        resp = self.client.post("/api/v1/auth/refresh/", {"refresh": str(refresh)}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)

    def test_logout(self):
        user = User.objects.create_user(username="logoutuser", password="Password123")
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + str(refresh.access_token))

        resp = self.client.post("/api/v1/auth/logout/", {"refresh": str(refresh)}, format="json")
        self.assertEqual(resp.status_code, 200)

    def test_change_password(self):
        user = User.objects.create_user(username="changepass", password="OldPassword123")
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + str(refresh.access_token))

        resp = self.client.post(
            "/api/v1/auth/change-password/",
            {"old_password": "OldPassword123", "new_password": "NewPassword123"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("tokens", resp.data)
        user.refresh_from_db()
        self.assertTrue(user.check_password("NewPassword123"))

    def test_reset_password(self):
        from myapp.models import PasswordResetOTP
        user = User.objects.create_user(username="resetuser", email="reset@example.com", password="OldPassword123")
        
        # 1. Request reset OTP
        resp1 = self.client.post("/api/v1/auth/reset-password/", {"email": "reset@example.com"}, format="json")
        self.assertEqual(resp1.status_code, 200)

        otp_record = PasswordResetOTP.objects.filter(user=user, is_used=False).first()
        self.assertIsNotNone(otp_record)

        # 2. Confirm reset with correct OTP
        resp2 = self.client.post(
            "/api/v1/auth/reset-password/confirm/",
            {"email": "reset@example.com", "otp_code": otp_record.otp_code, "new_password": "ResetPassword123"},
            format="json",
        )
        self.assertEqual(resp2.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.check_password("ResetPassword123"))

        # 3. Verify OTP is marked as used
        otp_record.refresh_from_db()
        self.assertTrue(otp_record.is_used)

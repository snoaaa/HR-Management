from django.test import TestCase

from .models import CompanyIdentity


class CompanyLogoTests(TestCase):
    def test_logo_upload_appears_on_documents(self):
        import io
        import shutil
        import tempfile

        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test import override_settings
        from PIL import Image

        from core.pdf import company_context
        from core.testing import client_for, make_user
        from users.models import User

        media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media, ignore_errors=True)
        with override_settings(MEDIA_ROOT=media):
            company = CompanyIdentity.objects.create(
                corporate_name="Saint Jean Services SA",
                legal_form="SA",
                address="Douala",
                legal_representative="J. Mbarga",
            )
            client = client_for(
                make_user("admin_logo", User.Roles.SYSTEM_ADMINISTRATOR)
            )
            buffer = io.BytesIO()
            Image.new("RGB", (40, 20), "#714B67").save(buffer, "PNG")
            upload = SimpleUploadedFile("logo.png", buffer.getvalue(), "image/png")
            url = f"/api/organisation/company-identity/{company.pk}/logo/"
            response = client.post(url, {"logo": upload}, format="multipart")
            self.assertEqual(response.status_code, 200, response.content)
            self.assertTrue(company_context()["company_logo_path"])
            fake = SimpleUploadedFile("logo.png", b"not an image", "image/png")
            self.assertEqual(
                client.post(url, {"logo": fake}, format="multipart").status_code, 400
            )
            current = self.client.get("/api/organisation/company-identity/current/")
            self.assertEqual(current.status_code, 200)
            self.assertIn("logo", current.json())
            self.assertEqual(client.delete(url).status_code, 200)
            self.assertIsNone(company_context()["company_logo_path"])

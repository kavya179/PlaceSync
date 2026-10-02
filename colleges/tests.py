from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from colleges.models import College, CampusImage
from PIL import Image
import io

User = get_user_model()

class CollegeProfileTestCase(TestCase):
    def setUp(self):
        self.college = College.objects.create(
            name="Test Engineering College",
            code="TEC",
            website="https://tec.edu"
        )
        self.user = User.objects.create_user(
            username="tec_admin",
            email="admin@tec.edu",
            password="password123",
            role=User.Role.COLLEGE_ADMIN,
            college=self.college
        )
        self.client = Client()
        self.client.login(username="tec_admin", password="password123")

    def make_jfif_image(self, filename):
        img = Image.new('RGB', (100, 100), color='blue')
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        buf.seek(0)
        return SimpleUploadedFile(filename, buf.getvalue(), content_type="image/jfif")

    def test_upload_multiple_jfif_campus_images(self):
        edit_url = reverse('colleges:profile_edit')
        img1 = self.make_jfif_image("1.jfif")
        img2 = self.make_jfif_image("2.jfif")
        img3 = self.make_jfif_image("3.jfif")

        response = self.client.post(edit_url, {
            'name': self.college.name,
            'university': 'Test University',
            'address': '123 Main St',
            'website': 'https://tec.edu',
            'email': 'admin@tec.edu',
            'phone': '1234567890',
            'campus_images': [img1, img2, img3]
        })

        self.assertRedirects(response, reverse('colleges:profile_detail'))
        self.assertEqual(CampusImage.objects.filter(college=self.college).count(), 3)

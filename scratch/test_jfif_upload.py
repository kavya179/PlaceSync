import os
import sys
import django
from django.core.files.uploadedfile import SimpleUploadedFile

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PlaceSync.settings')
django.setup()

from colleges.models import College, CampusImage
from PIL import Image
import io

# Create a sample JFIF image using Pillow
img = Image.new('RGB', (100, 100), color = 'red')
buf = io.BytesIO()
img.save(buf, format='JPEG')
buf.seek(0)

jfif_file = SimpleUploadedFile("test_photo.jfif", buf.getvalue(), content_type="image/jfif")

c = College.objects.first()
print("College:", c)
try:
    ci = CampusImage.objects.create(college=c, image=jfif_file)
    print("Created CampusImage successfully:", ci.id, ci.image.url)
except Exception as e:
    print("Failed to create CampusImage:", e)

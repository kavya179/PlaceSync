import os
import sys
import django
from django.core.files.uploadedfile import SimpleUploadedFile

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PlaceSync.settings')
django.setup()

from colleges.models import College, CampusImage
from colleges.forms import CollegeProfileForm
from PIL import Image
import io

c = College.objects.first()

def make_jfif(name):
    img = Image.new('RGB', (100, 100), color = 'blue')
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    buf.seek(0)
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/jfif")

f1 = make_jfif("1.jfif")
f2 = make_jfif("2.jfif")
f3 = make_jfif("3.jfif")

from django.utils.datastructures import MultiValueDict

files_dict = MultiValueDict({'campus_images': [f1, f2, f3]})
data = {
    'name': c.name,
    'university': c.university,
    'address': c.address,
    'website': c.website,
    'email': c.email,
    'phone': c.phone,
    'linkedin': c.linkedin,
    'twitter': c.twitter,
    'instagram': c.instagram,
}

form = CollegeProfileForm(data=data, files=files_dict, instance=c)
print("Form is_valid():", form.is_valid())
if not form.is_valid():
    print("Form errors:", form.errors)
else:
    print("Cleaned data keys:", form.cleaned_data.keys())

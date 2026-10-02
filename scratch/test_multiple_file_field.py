import os
import sys
import django
from django.core.files.uploadedfile import SimpleUploadedFile

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PlaceSync.settings')
django.setup()

from django import forms
from colleges.models import College, CampusImage
from PIL import Image
import io

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={
            'class': 'form-input',
            'accept': 'image/*,.jfif,.jpg,.jpeg,.png,.gif,.webp'
        }))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        if not data:
            return []
        single_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_clean(d, initial) for d in data if d]
        else:
            return [single_clean(data, initial)] if data else []

class TestCollegeProfileForm(forms.ModelForm):
    campus_images = MultipleFileField(
        required=False,
        label="Upload Campus Images"
    )

    class Meta:
        model = College
        fields = ['name', 'university', 'address', 'website', 'email', 'phone', 'logo', 'linkedin', 'twitter', 'instagram']

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

form = TestCollegeProfileForm(data=data, files=files_dict, instance=c)
print("Form is_valid():", form.is_valid())
if not form.is_valid():
    print("Form errors:", form.errors)
else:
    print("Form is VALID! Cleaned campus_images:", form.cleaned_data.get('campus_images'))

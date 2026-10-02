import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PlaceSync.settings')
django.setup()

from django.apps import apps
from django.contrib.auth import get_user_model
from colleges.models import College

User = get_user_model()

mit_college = College.objects.get(id=1)
ljiet_college = College.objects.get(id=4)
mit_user = User.objects.filter(username='mitadmin').first()
ljiet_user = User.objects.filter(username='admin_ljiet').first()

print(f"MIT College (ID 1): {mit_college.name} (Code: {mit_college.code})")
print(f"LJIET College (ID 4): {ljiet_college.name} (Code: {ljiet_college.code})")
print(f"mitadmin User: {mit_user}")
print(f"admin_ljiet User: {ljiet_user}")
print("=" * 60)

for model in apps.get_models():
    model_name = model._meta.label
    # Check fields of model
    field_names = [f.name for f in model._meta.fields]
    
    # Check counts for MIT college / user vs LJIET college / user
    q_mit = None
    q_ljiet = None
    
    counts = {}
    if 'college' in field_names:
        counts['mit_by_college'] = model.objects.filter(college=mit_college).count()
        counts['ljiet_by_college'] = model.objects.filter(college=ljiet_college).count()
    
    if 'user' in field_names and mit_user:
        counts['mit_by_user'] = model.objects.filter(user=mit_user).count()
        counts['ljiet_by_user'] = model.objects.filter(user=ljiet_user).count()
        
    if 'created_by' in field_names and mit_user:
        counts['mit_by_created_by'] = model.objects.filter(created_by=mit_user).count()
        counts['ljiet_by_created_by'] = model.objects.filter(created_by=ljiet_user).count()
        
    if counts:
        print(f"Model: {model_name} | Field counts: {counts}")

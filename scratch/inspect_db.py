import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PlaceSync.settings')
django.setup()

from colleges.models import College
from django.contrib.auth import get_user_model
User = get_user_model()

print("=== COLLEGES ===")
for c in College.objects.all():
    print(f"ID: {c.id} | Name: '{c.name}' | Code: '{c.code}'")

print("\n=== USERS ===")
for u in User.objects.all():
    c_name = u.college.name if getattr(u, 'college', None) else "None"
    print(f"ID: {u.id} | Username: '{u.username}' | Email: '{u.email}' | Role: '{getattr(u, 'role', None)}' | College: '{c_name}'")

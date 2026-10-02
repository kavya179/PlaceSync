import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PlaceSync.settings')
django.setup()

from students.models import Student
from django.contrib.auth import get_user_model

User = get_user_model()

print("=== ALL STUDENTS ===")
for s in Student.objects.all():
    print(f"ID: {s.id} | Roll: '{s.roll_number}' | Name: '{s.name}' | Email: '{s.email}' | User: {s.user.username if s.user else 'None'}")

print("\n=== ALL USERS (STUDENT ROLE) ===")
for u in User.objects.filter(role=User.Role.STUDENT):
    print(f"ID: {u.id} | Username: '{u.username}' | Email: '{u.email}' | College: {u.college}")

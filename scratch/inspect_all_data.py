import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PlaceSync.settings')
django.setup()

from django.apps import apps
from colleges.models import College
from django.contrib.auth import get_user_model

User = get_user_model()
c1 = College.objects.get(id=1)
c4 = College.objects.get(id=4)
mitadmin = User.objects.get(username='mitadmin')
admin_ljiet = User.objects.get(username='admin_ljiet')

print("=== STUDENTS for College 1 ===")
Student = apps.get_model('students', 'Student')
for s in Student.objects.filter(college=c1):
    print(f"Student ID: {s.id}, Name: {getattr(s, 'full_name', getattr(s, 'name', '') or getattr(s, 'first_name', '')), }, Email: {s.email}, Dept: {s.department}, Batch: {s.batch}, User: {s.user}")

print("\n=== COMPANIES for College 1 ===")
Company = apps.get_model('companies', 'Company')
for comp in Company.objects.filter(college=c1):
    print(f"Company ID: {comp.id}, Name: {comp.name}, College: {comp.college}")

print("\n=== PLACEMENT DRIVES for College 1 ===")
PlacementDrive = apps.get_model('placements', 'PlacementDrive')
for pd in PlacementDrive.objects.filter(college=c1):
    print(f"Drive ID: {pd.id}, Title: {pd.title}, Company: {pd.company}, College: {pd.college}")

print("\n=== APPLICATIONS ===")
Application = apps.get_model('placements', 'Application')
for app in Application.objects.all():
    print(f"App ID: {app.id}, Student: {app.student}, Drive: {app.drive}, Status: {getattr(app, 'status', '')}")

print("\n=== OPPORTUNITIES for College 1 ===")
ScrapedOpportunity = apps.get_model('opportunities', 'ScrapedOpportunity')
for opp in ScrapedOpportunity.objects.filter(college=c1):
    print(f"Opp ID: {opp.id}, Title: {opp.title}, Company: {getattr(opp, 'company_name', getattr(opp, 'company', ''))}")

print("\n=== STAFF MEMBERS for College 1 ===")
StaffMember = apps.get_model('staff_permissions', 'StaffMember')
for sm in StaffMember.objects.filter(college=c1):
    print(f"Staff ID: {sm.id}, User: {sm.user.username}, Role: {sm.role}, Dept: {sm.department}")

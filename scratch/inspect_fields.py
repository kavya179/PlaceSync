import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PlaceSync.settings')
django.setup()

from django.apps import apps
from colleges.models import College

c1 = College.objects.get(id=1)
c4 = College.objects.get(id=4)

PlacementDrive = apps.get_model('placements', 'PlacementDrive')
print("PlacementDrive fields:", [f.name for f in PlacementDrive._meta.fields])
for pd in PlacementDrive.objects.filter(college=c1):
    print("Drive:", pd.__dict__)

ScrapedOpportunity = apps.get_model('opportunities', 'ScrapedOpportunity')
print("\nScrapedOpportunity fields:", [f.name for f in ScrapedOpportunity._meta.fields])
for opp in ScrapedOpportunity.objects.filter(college=c1):
    print("Opp:", opp.__dict__)

StaffMember = apps.get_model('staff_permissions', 'StaffMember')
print("\nStaffMember fields:", [f.name for f in StaffMember._meta.fields])
for sm in StaffMember.objects.filter(college=c1):
    print("StaffMember:", sm.__dict__)

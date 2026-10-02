import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PlaceSync.settings')
django.setup()

from django.apps import apps
from django.db import transaction
from colleges.models import College
from django.contrib.auth import get_user_model

User = get_user_model()

with transaction.atomic():
    c1 = College.objects.get(id=1)
    c4 = College.objects.get(id=4)
    print(f"Transferring data from College '{c1.name}' (ID {c1.id}) to College '{c4.name}' (ID {c4.id})")

    Department = apps.get_model('departments', 'Department')
    Batch = apps.get_model('batches', 'Batch')
    Student = apps.get_model('students', 'Student')
    Company = apps.get_model('companies', 'Company')
    PlacementDrive = apps.get_model('placements', 'PlacementDrive')
    ScrapedOpportunity = apps.get_model('opportunities', 'ScrapedOpportunity')
    StaffMember = apps.get_model('staff_permissions', 'StaffMember')

    # Department Mapping
    # c1 Dept 1 (CSE) -> c4 Dept 6 (CSE)
    # c1 Dept 4 (abc) -> c4 Dept 5 (IT)
    dept_c4_cse = Department.objects.get(id=6, college=c4)
    dept_c4_it = Department.objects.get(id=5, college=c4)

    dept_map = {
        1: dept_c4_cse,
        4: dept_c4_it
    }

    # 1. Update Batches
    batches_c1 = Batch.objects.filter(department__college=c1)
    for b in batches_c1:
        old_dept_id = b.department_id
        if old_dept_id in dept_map:
            b.department = dept_map[old_dept_id]
            b.save()
            print(f"Updated Batch '{b.name}' (ID {b.id}) to Department '{b.department.name}' (College LJIET)")

    # 2. Update Students
    students_c1 = Student.objects.filter(college=c1)
    for s in students_c1:
        s.college = c4
        if s.department_id in dept_map:
            s.department = dept_map[s.department_id]
        s.save()
        print(f"Updated Student '{s.first_name if hasattr(s, 'first_name') else s}' (ID {s.id}) to College LJIET")

    # 3. Update Companies
    companies_c1 = Company.objects.filter(college=c1)
    for comp in companies_c1:
        comp.college = c4
        comp.save()
        print(f"Updated Company '{comp.name}' (ID {comp.id}) to College LJIET")

    # 4. Update Placement Drives
    drives_c1 = PlacementDrive.objects.filter(college=c1)
    for pd in drives_c1:
        pd.college = c4
        pd.save()
        print(f"Updated PlacementDrive '{pd.role}' (ID {pd.id}) to College LJIET")

    # 5. Update Scraped Opportunities
    opps_c1 = ScrapedOpportunity.objects.filter(college=c1)
    for opp in opps_c1:
        opp.college = c4
        opp.save()
        print(f"Updated ScrapedOpportunity '{opp.company_name} - {opp.role}' (ID {opp.id}) to College LJIET")

    # 6. Update Staff Members
    staff_c1 = StaffMember.objects.filter(college=c1)
    for sm in staff_c1:
        sm.college = c4
        if getattr(sm, 'department_id', None) in dept_map:
            sm.department = dept_map[sm.department_id]
        sm.save()
        print(f"Updated StaffMember user '{sm.user.username}' (ID {sm.id}) to College LJIET")

    # 7. Update Users
    users_c1 = User.objects.filter(college=c1)
    for u in users_c1:
        u.college = c4
        u.save()
        print(f"Updated User '{u.username}' (ID {u.id}) to College LJIET")

print("\nData transfer complete successfully!")

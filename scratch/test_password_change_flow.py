import os
import sys
import django
from django.test import Client
from django.urls import reverse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PlaceSync.settings')
django.setup()

from django.contrib.auth import get_user_model
from colleges.models import College
from departments.models import Department
from batches.models import Batch
from students.models import Student

User = get_user_model()

print("Setting up test data...")
college = College.objects.first()
dept = Department.objects.filter(college=college).first()
if not dept:
    dept = Department.objects.create(college=college, name="Computer Science Test", code="CST")
batch = Batch.objects.filter(department=dept).first()
if not batch:
    batch = Batch.objects.create(department=dept, name="2027 CS TEST", graduation_year=2027)

enrollment_no = "24002170210099"
initial_password = "DefaultPassword@123"
new_password = "MyNewSecretPassword@456"

# Cleanup any existing test records
User.objects.filter(username=enrollment_no).delete()
Student.objects.filter(roll_number=enrollment_no).delete()

user = User.objects.create_user(
    username=enrollment_no,
    email="student99@ftc.edu",
    password=initial_password,
    role=User.Role.STUDENT,
    college=college
)
user.must_change_password = True
user.save()

student = Student.objects.create(
    user=user,
    college=college,
    department=dept,
    batch=batch,
    roll_number=enrollment_no,
    name="Test Student 99",
    email="student99@ftc.edu"
)

print(f"Created Student '{student.name}' (Enrollment: {enrollment_no}) with must_change_password={user.must_change_password}")

client = Client()

login_url = reverse('accounts:student_login')
change_url = reverse('accounts:password_change')
portal_url = reverse('student_portal:dashboard')
logout_url = reverse('accounts:logout')

print(f"URLs -> Login: {login_url}, Change: {change_url}, Portal: {portal_url}")

# Step 1: Login with initial default password
print("\nStep 1: Logging in with initial default password...")
login_response = client.post(login_url, {
    'username': enrollment_no,
    'password': initial_password
})
print(f"Login response status: {login_response.status_code}")
assert login_response.status_code == 302, "Login should redirect after authentication"

# Step 2: Try accessing student portal dashboard
print("\nStep 2: Trying to access Student Portal Dashboard...")
dashboard_response = client.get(portal_url)
print(f"Dashboard response status: {dashboard_response.status_code}")
print(f"Redirected location: {dashboard_response.headers.get('Location')}")
assert dashboard_response.status_code == 302, "Must redirect when must_change_password is True!"
assert change_url in dashboard_response.headers.get('Location'), f"Should be redirected to {change_url}!"

# Step 3: Change password
print("\nStep 3: Submitting new password on password-change page...")
change_response = client.post(change_url, {
    'old_password': initial_password,
    'new_password1': new_password,
    'new_password2': new_password
})
print(f"Password change response status: {change_response.status_code}")
print(f"Redirected location after change: {change_response.headers.get('Location')}")
assert change_response.status_code == 302, "Password change should redirect on success"

# Refresh user from DB
user.refresh_from_db()
print(f"User must_change_password after change: {user.must_change_password}")
assert user.must_change_password == False, "must_change_password should now be False!"
assert user.check_password(new_password) == True, "New password should be set!"

# Step 4: Logout
print("\nStep 4: Logging out...")
logout_response = client.get(logout_url)
print(f"Logout status: {logout_response.status_code}")

# Step 5: Login with OLD password (should fail)
print("\nStep 5: Trying to log in with OLD password...")
old_login_response = client.post(login_url, {
    'username': enrollment_no,
    'password': initial_password
})
assert old_login_response.status_code == 200, "Old password login should be rejected!"
print("Old password login correctly REJECTED!")

# Step 6: Login with NEW password (should succeed and grant full access)
print("\nStep 6: Logging in with NEW password...")
new_login_response = client.post(login_url, {
    'username': enrollment_no,
    'password': new_password
})
print(f"New password login response status: {new_login_response.status_code}")
assert new_login_response.status_code == 302, "New password login should succeed!"

portal_access = client.get(portal_url)
print(f"Student Portal access with new password status: {portal_access.status_code}")
assert portal_access.status_code == 200, "Student should have full dashboard access with new password!"

# Cleanup test user & student
user.delete()

print("\n============================================================")
print("SUCCESS! The first-login password change flow works 100% PERFECTLY!")
print("============================================================")

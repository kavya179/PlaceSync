import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PlaceSync.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()
common_passwords = ['Admin@123', 'admin', 'admin123', 'password', 'ljiet123', 'ljiet', 'mitadmin', 'admin@gmail.com']

for username in ['mitadmin', 'admin_ljiet']:
    user = User.objects.filter(username=username).first()
    if user:
        found = False
        for pw in common_passwords:
            if user.check_password(pw):
                print(f"User {username} password match: '{pw}'")
                found = True
                break
        if not found:
            print(f"User {username} password hash: {user.password[:30]}...")

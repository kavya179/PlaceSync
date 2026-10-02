import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PlaceSync.settings')
django.setup()

from django.apps import apps

for model in apps.get_models():
    print(f"App: {model._meta.app_label} | Model: {model._meta.model_name} | Table: {model._meta.db_table}")

import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PlaceSync.settings')
django.setup()

from django.apps import apps
from django.db import models

for model in apps.get_models():
    print(f"\n--- {model._meta.label} ---")
    for field in model._meta.get_fields():
        if field.is_relation:
            target = field.related_model._meta.label if field.related_model else "None"
            print(f"  Relation field: {field.name} ({field.__class__.__name__}) -> {target}")
        else:
            print(f"  Scalar field: {field.name} ({field.__class__.__name__})")

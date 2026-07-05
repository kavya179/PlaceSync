from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db import transaction
from django.contrib.auth import get_user_model
from django.db.models import Q, Max, Avg
from django.http import Http404
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import pandas as pd
import re

from .models import Batch
from .forms import BatchForm
from students.models import Student

User = get_user_model()

class BatchListView(LoginRequiredMixin, View):
    template_name = 'batches/batch_list.html'

    def get(self, request, *args, **kwargs):
        college = request.user.college
        if not college:
            raise Http404("No college associated with your account.")

        # Scoped to college departments
        batches = Batch.objects.filter(department__college=college).order_by('-graduation_year', 'name')

        # Search query logic
        q = request.GET.get('q', '').strip()
        if q:
            batches = batches.filter(
                Q(name__icontains=q) | 
                Q(department__name__icontains=q) | 
                Q(department__code__icontains=q)
            )

        return render(request, self.template_name, {
            'batches': batches,
            'q': q
        })


class BatchCreateView(LoginRequiredMixin, View):
    form_class = BatchForm
    template_name = 'batches/batch_form.html'

    def get(self, request, *args, **kwargs):
        form = self.form_class(college=request.user.college)
        return render(request, self.template_name, {'form': form, 'action': 'Add'})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, college=request.user.college)
        if form.is_valid():
            batch = form.save()
            messages.success(request, f"Batch '{batch.name}' has been created successfully.")
            return redirect('batches:list')
        return render(request, self.template_name, {'form': form, 'action': 'Add'})


class BatchUpdateView(LoginRequiredMixin, View):
    form_class = BatchForm
    template_name = 'batches/batch_form.html'

    def get(self, request, pk, *args, **kwargs):
        batch = get_object_or_404(Batch, pk=pk, department__college=request.user.college)
        form = self.form_class(instance=batch, college=request.user.college)
        return render(request, self.template_name, {'form': form, 'action': 'Edit', 'batch': batch})

    def post(self, request, pk, *args, **kwargs):
        batch = get_object_or_404(Batch, pk=pk, department__college=request.user.college)
        form = self.form_class(request.POST, instance=batch, college=request.user.college)
        if form.is_valid():
            form.save()
            messages.success(request, f"Batch '{batch.name}' details have been updated.")
            return redirect('batches:list')
        return render(request, self.template_name, {'form': form, 'action': 'Edit', 'batch': batch})


class BatchDeleteView(LoginRequiredMixin, View):
    template_name = 'batches/batch_confirm_delete.html'

    def get(self, request, pk, *args, **kwargs):
        batch = get_object_or_404(Batch, pk=pk, department__college=request.user.college)
        return render(request, self.template_name, {'batch': batch})

    def post(self, request, pk, *args, **kwargs):
        batch = get_object_or_404(Batch, pk=pk, department__college=request.user.college)
        name = batch.name
        batch.delete()
        messages.success(request, f"Batch '{name}' has been deleted successfully.")
        return redirect('batches:list')


class BatchDashboardView(LoginRequiredMixin, View):
    template_name = 'batches/batch_dashboard.html'

    def get(self, request, pk, *args, **kwargs):
        batch = get_object_or_404(Batch, pk=pk, department__college=request.user.college)
        
        # All students in this batch
        all_students = batch.students.all()
        
        # Calculate statistics
        total_students = all_students.count()
        
        # Placed status includes PLACED and PLACED_AND_INTERN
        placed_students = all_students.filter(
            placement_status__in=['PLACED', 'PLACED_AND_INTERN']
        ).count()
        
        # Internship status includes INTERN and PLACED_AND_INTERN
        internship_students = all_students.filter(
            placement_status__in=['INTERN', 'PLACED_AND_INTERN']
        ).count()
        
        placement_pct = (placed_students / total_students * 100) if total_students > 0 else 0.0
        
        # package & stipend aggregation calculations
        placed_qs = all_students.filter(placement_status__in=['PLACED', 'PLACED_AND_INTERN'])
        highest_pkg = placed_qs.aggregate(Max('package_amount'))['package_amount__max'] or 0.0
        avg_pkg = placed_qs.aggregate(Avg('package_amount'))['package_amount__avg'] or 0.0
        
        intern_qs = all_students.filter(placement_status__in=['INTERN', 'PLACED_AND_INTERN'])
        highest_stipend = intern_qs.aggregate(Max('stipend_amount'))['stipend_amount__max'] or 0.0
        avg_stipend = intern_qs.aggregate(Avg('stipend_amount'))['stipend_amount__avg'] or 0.0

        stats = {
            'total_students': total_students,
            'placed_students': placed_students,
            'internship_students': internship_students,
            'placement_percentage': round(placement_pct, 1),
            'highest_package': round(highest_pkg, 2),
            'average_package': round(avg_pkg, 2),
            'highest_stipend': round(highest_stipend, 2),
            'average_stipend': round(avg_stipend, 2),
        }

        # Handle student search filtering inside list
        students = all_students
        q = request.GET.get('q', '').strip()
        if q:
            students = students.filter(
                Q(name__icontains=q) | 
                Q(roll_number__icontains=q) | 
                Q(placement_status__icontains=q)
            )

        context = {
            'batch': batch,
            'stats': stats,
            'students': students,
            'q': q
        }
        return render(request, self.template_name, context)


class BatchStudentImportView(LoginRequiredMixin, View):
    template_name = 'batches/student_import.html'

    def get(self, request, pk, *args, **kwargs):
        batch = get_object_or_404(Batch, pk=pk, department__college=request.user.college)
        return render(request, self.template_name, {'batch': batch})

    def post(self, request, pk, *args, **kwargs):
        batch = get_object_or_404(Batch, pk=pk, department__college=request.user.college)
        default_password = request.POST.get('default_password', '').strip()
        csv_file = request.FILES.get('csv_file')

        errors = []

        if not default_password:
            errors.append("Default password is required.")
        if len(default_password) < 6:
            errors.append("Default password must be at least 6 characters long.")
        if not csv_file:
            errors.append("Please upload a CSV file.")

        if errors:
            return render(request, self.template_name, {'batch': batch, 'errors': errors})

        try:
            # Parse using Pandas
            df = pd.read_csv(csv_file, dtype=str)
            
            # Clean headers: lowercase and stripped
            df.columns = [str(c).strip().lower() for c in df.columns]
            
            # Map required columns
            required_cols = ['roll_number', 'name', 'email']
            missing_cols = [c for c in required_cols if c not in df.columns]
            if missing_cols:
                errors.append(f"CSV is missing required columns: {', '.join(missing_cols)}.")
                return render(request, self.template_name, {'batch': batch, 'errors': errors})

            # Clean dataframe: fill nan with empty and convert all to string
            df = df.fillna('').astype(str)
            for c in df.columns:
                df[c] = df[c].str.strip()

            # Ensure phone column exists
            if 'phone' not in df.columns:
                df['phone'] = ''

            # Rows validation
            rolls_seen = set()
            emails_seen = set()
            valid_records = []

            for idx, row in df.iterrows():
                row_num = idx + 2 # 1-based index + header row = idx + 2
                roll = row['roll_number']
                name = row['name']
                email = row['email']
                phone = row.get('phone', '')

                # Skip completely empty rows
                if not roll and not name and not email and not phone:
                    continue

                if not roll:
                    errors.append(f"Row {row_num}: Roll Number is empty.")
                if not name:
                    errors.append(f"Row {row_num}: Student Name is empty.")
                if not email:
                    errors.append(f"Row {row_num}: Email Address is empty.")
                else:
                    try:
                        validate_email(email)
                    except ValidationError:
                        errors.append(f"Row {row_num}: Email '{email}' is invalid.")

                # Unique constraints in CSV itself
                if roll:
                    roll_lower = roll.lower()
                    if roll_lower in rolls_seen:
                        errors.append(f"Row {row_num}: Duplicate Roll Number '{roll}' within CSV.")
                    else:
                        rolls_seen.add(roll_lower)

                if email:
                    email_lower = email.lower()
                    if email_lower in emails_seen:
                        errors.append(f"Row {row_num}: Duplicate Email '{email}' within CSV.")
                    else:
                        emails_seen.add(email_lower)

                # Database existence check
                if roll:
                    if Student.objects.filter(college=request.user.college, roll_number__iexact=roll).exists():
                        errors.append(f"Row {row_num}: Roll Number '{roll}' is already registered in your college.")
                    if User.objects.filter(username__iexact=roll).exists():
                        errors.append(f"Row {row_num}: Roll Number (Username) '{roll}' is already registered in the system.")
                if email:
                    if User.objects.filter(email__iexact=email).exists():
                        errors.append(f"Row {row_num}: Email '{email}' is already registered in the system.")

                valid_records.append({
                    'roll_number': roll,
                    'name': name,
                    'email': email,
                    'phone': phone
                })

            if errors:
                return render(request, self.template_name, {'batch': batch, 'errors': errors[:50]}) # cap to first 50 errors

            # Validation succeeded, save to session and redirect
            request.session['import_preview_data'] = valid_records
            request.session['import_default_password'] = default_password

            return redirect('batches:import_preview', pk=batch.pk)

        except Exception as e:
            errors.append(f"Failed to parse CSV file: {str(e)}")
            return render(request, self.template_name, {'batch': batch, 'errors': errors})



class BatchStudentImportPreviewView(LoginRequiredMixin, View):
    template_name = 'batches/student_import_preview.html'

    def get(self, request, pk, *args, **kwargs):
        batch = get_object_or_404(Batch, pk=pk, department__college=request.user.college)
        records = request.session.get('import_preview_data')
        default_password = request.session.get('import_default_password')

        if not records or not default_password:
            messages.error(request, "No import preview session found. Please upload CSV first.")
            return redirect('batches:import_students', pk=batch.pk)

        return render(request, self.template_name, {
            'batch': batch,
            'records': records,
            'total_count': len(records),
            'default_password': default_password
        })

    def post(self, request, pk, *args, **kwargs):
        batch = get_object_or_404(Batch, pk=pk, department__college=request.user.college)
        records = request.session.get('import_preview_data')
        default_password = request.session.get('import_default_password')

        if not records or not default_password:
            messages.error(request, "Import session expired or invalid. Please re-upload.")
            return redirect('batches:import_students', pk=batch.pk)

        college = request.user.college

        # Database Insertion
        imported_list = []
        try:
            with transaction.atomic():
                for row in records:
                    roll = row['roll_number'].strip()
                    name = row['name'].strip()
                    email = row['email'].strip()
                    phone = row.get('phone', '').strip()

                    # 1. Create custom User account
                    user = User.objects.create_user(
                        username=roll, # Username is the Enrollment Number
                        email=email,
                        password=default_password,
                        role=User.Role.STUDENT,
                        college=college
                    )
                    user.must_change_password = True
                    user.save()

                    # 2. Create Student Profile
                    student = Student.objects.create(
                        user=user,
                        college=college,
                        department=batch.department,
                        batch=batch,
                        roll_number=roll,
                        name=name,
                        email=email,
                        phone=phone
                    )
                    
                    imported_list.append({
                        'roll_number': roll,
                        'name': name,
                        'email': email,
                        'phone': phone
                    })

            # Save report to session and clean temporary data
            request.session.pop('import_preview_data', None)
            request.session.pop('import_default_password', None)
            
            request.session['import_report'] = {
                'batch_name': batch.name,
                'total_imported': len(imported_list),
                'default_password': default_password,
                'students': imported_list
            }

            messages.success(request, f"Imported {len(imported_list)} student accounts successfully.")
            return redirect('batches:import_report', pk=batch.pk)

        except Exception as e:
            messages.error(request, f"Database transaction failed: {str(e)}")
            return redirect('batches:import_preview', pk=batch.pk)


class BatchStudentImportReportView(LoginRequiredMixin, View):
    template_name = 'batches/student_import_report.html'

    def get(self, request, pk, *args, **kwargs):
        batch = get_object_or_404(Batch, pk=pk, department__college=request.user.college)
        report = request.session.pop('import_report', None) # Read once and clear

        if not report:
            messages.error(request, "No import report found or it has already expired.")
            return redirect('batches:dashboard', pk=batch.pk)

        return render(request, self.template_name, {
            'batch': batch,
            'report': report
        })


from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
import datetime
from django.views import View
from django.http import FileResponse, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Sum

from students.models import (
    Student, StudentSkill, StudentResume, Project,
    TechnicalLinks, Activity, WeeklySummary, MonthlySummary, ProjectMilestone,
    HackathonJournal, CodingPractice, LearningJournal, OpenSourceContribution,
    LearningGoal, DeveloperAchievement, Certificate
)
from placements.models import PlacementDrive, Application, DriveBookmark, PlacementCalendarEvent
from communication.models import Notification
from opportunities.models import ScrapedOpportunity
from .forms import (
    StudentSkillForm, ResumeUploadForm, ProjectForm,
    TechnicalLinksForm, ActivityForm, WeeklySummaryForm, MonthlySummaryForm, ProjectMilestoneForm,
    HackathonJournalForm, CodingPracticeForm, LearningJournalForm, OpenSourceContributionForm,
    LearningGoalForm, DeveloperAchievementForm, CertificateForm, PersonalProfileForm, AcademicProfileForm
)
from .resume_analyzer import extract_pdf_text, analyze_resume_text
import json


# ─────────────────────────────────────────────────────────────────────────────
# Mixin: enforce student login + role guard
# ─────────────────────────────────────────────────────────────────────────────

class StudentRequiredMixin(LoginRequiredMixin):
    """Redirect to student login if user is not a STUDENT."""
    login_url = 'accounts:student_login'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role != 'STUDENT':
            # Admin trying to access student portal → send to admin dashboard
            return redirect('dashboard:index')
        return super().dispatch(request, *args, **kwargs)


def _get_student(request):
    """Helper: fetch Student profile for the current user."""
    try:
        return request.user.student_profile
    except Student.DoesNotExist:
        return None


def _base_ctx(request, student=None):
    """Common context keys needed by student_portal/base.html (sidebar badge etc.)"""
    unread = 0
    if request.user.is_authenticated:
        unread = Notification.objects.filter(user=request.user, is_read=False).count()
    return {
        'student': student or _get_student(request),
        'unread_count': unread,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────────────────────────────────────

class StudentDashboardView(StudentRequiredMixin, View):
    template_name = 'student_portal/dashboard.html'

    def get(self, request, *args, **kwargs):
        student = _get_student(request)
        if not student:
            messages.error(request, "No student profile linked to your account.")
            return redirect('accounts:logout')

        applications = Application.objects.filter(student=student)
        app_count = applications.count()
        interview_count = applications.filter(
            status__in=['SHORTLISTED', 'SELECTED']
        ).count()
        offer_count = applications.filter(status='SELECTED').count()

        notif_count = Notification.objects.filter(
            user=request.user, is_read=False
        ).count()
        recent_notifs = Notification.objects.filter(
            user=request.user
        ).order_by('-created_at')[:5]

        # Open drives eligible for this student
        open_drives = PlacementDrive.objects.filter(
            college=student.college,
            status__in=['UPCOMING', 'ACTIVE'],
            eligible_departments=student.department,
        ).exclude(
            applications__student=student
        ).filter(
            min_cgpa__lte=student.cgpa or 0,
            max_backlogs__gte=student.backlogs,
        )[:5]

        # Upcoming deadlines (drives with deadlines in the future)
        upcoming_deadlines = PlacementDrive.objects.filter(
            college=student.college,
            status__in=['UPCOMING', 'ACTIVE'],
            deadline__isnull=False,
            deadline__gte=timezone.now().date(),
        ).order_by('deadline')[:5]

        recent_applications = applications.select_related(
            'drive', 'drive__company'
        ).order_by('-applied_at')[:5]

        # Compute scores
        profile_pct = student.profile_completion()
        ats = student.ats_score()
        readiness = student.placement_readiness()
        career = student.career_score()

        context = {
            **_base_ctx(request, student),
            'app_count': app_count,
            'interview_count': interview_count,
            'offer_count': offer_count,
            'notif_count': notif_count,
            'recent_notifs': recent_notifs,
            'open_drives': open_drives,
            'upcoming_deadlines': upcoming_deadlines,
            'recent_applications': recent_applications,
            'profile_pct': profile_pct,
            'ats_score': ats,
            'readiness_score': readiness,
            'career_score': career,
            'resume_uploaded': bool(student.resume),
        }
        return render(request, self.template_name, context)


# ─────────────────────────────────────────────────────────────────────────────
# Profile: View
# ─────────────────────────────────────────────────────────────────────────────

class StudentProfileView(StudentRequiredMixin, View):
    template_name = 'student_portal/profile.html'

    def get(self, request, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return redirect('accounts:logout')
        return render(request, self.template_name, {
            **_base_ctx(request, student),
        })


# ─────────────────────────────────────────────────────────────────────────────
# Profile: Edit
# ─────────────────────────────────────────────────────────────────────────────

class StudentProfileEditView(StudentRequiredMixin, View):
    template_name = 'student_portal/profile_edit.html'

    def get(self, request, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return redirect('accounts:logout')
        form = PersonalProfileForm(instance=student)
        return render(request, self.template_name, {
            **_base_ctx(request, student),
            'form': form,
        })

    def post(self, request, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return redirect('accounts:logout')
        form = PersonalProfileForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, "Personal profile updated successfully.")
            return redirect('student_portal:profile')
        return render(request, self.template_name, {
            **_base_ctx(request, student),
            'form': form,
        })


class StudentAcademicProfileView(StudentRequiredMixin, View):
    template_name = 'student_portal/academic_profile.html'

    def get(self, request, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return redirect('accounts:logout')

        is_edit = (request.GET.get('edit') == '1')
        form = None
        if is_edit:
            form = AcademicProfileForm(instance=student)

        # Academic Performance List
        performances = list(student.semester_performances.all())
        if not performances:
            for sem in range(1, 9):
                if sem < student.semester:
                    status_val = "Completed"
                elif sem == student.semester:
                    status_val = "Current"
                else:
                    status_val = "Upcoming"
                
                performances.append({
                    'semester': sem,
                    'spi': None,
                    'status': status_val,
                })
        else:
            # Ensure semesters up to 8 are present in display list
            sem_map = {p.semester: p for p in performances}
            performances = []
            for sem in range(1, 9):
                if sem in sem_map:
                    performances.append(sem_map[sem])
                else:
                    if sem < student.semester:
                        status_val = "Completed"
                    elif sem == student.semester:
                        status_val = "Current"
                    else:
                        status_val = "Upcoming"
                    performances.append({
                        'semester': sem,
                        'spi': None,
                        'status': status_val,
                    })

        # Eligibility calculation
        min_required_cgpa = 6.00
        current_cgpa = float(student.cgpa or 0)
        is_eligible = (current_cgpa >= min_required_cgpa) and (student.backlogs == 0)

        # Academic Status description
        academic_status = "Not Eligible"
        if is_eligible:
            academic_status = "Eligible"

        # Calculate Completed Semesters count
        # A semester is completed if it is less than current semester and has an SPI set
        completed_count = student.semester_performances.filter(semester__lt=student.semester, spi__isnull=False).count()

        # Current Year text based on semester
        current_year_str = "1st Year"
        if student.semester in [3, 4]:
            current_year_str = "2nd Year"
        elif student.semester in [5, 6]:
            current_year_str = "3rd Year"
        elif student.semester in [7, 8]:
            current_year_str = "4th Year"

        context = {
            **_base_ctx(request, student),
            'performances': performances,
            'min_required_cgpa': min_required_cgpa,
            'is_eligible': is_eligible,
            'academic_status': academic_status,
            'completed_count': completed_count,
            'current_year_str': current_year_str,
            'is_edit': is_edit,
            'form': form,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return redirect('accounts:logout')
        
        form = AcademicProfileForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, "Academic profile updated successfully.")
            return redirect('student_portal:academic_profile')
        
        # If invalid, render form with errors
        # Academic Performance List
        performances = list(student.semester_performances.all())
        sem_map = {p.semester: p for p in performances}
        performances = []
        for sem in range(1, 9):
            if sem in sem_map:
                performances.append(sem_map[sem])
            else:
                if sem < student.semester:
                    status_val = "Completed"
                elif sem == student.semester:
                    status_val = "Current"
                else:
                    status_val = "Upcoming"
                performances.append({
                    'semester': sem,
                    'spi': None,
                    'status': status_val,
                })

        min_required_cgpa = 6.00
        current_cgpa = float(student.cgpa or 0)
        is_eligible = (current_cgpa >= min_required_cgpa) and (student.backlogs == 0)
        academic_status = "Not Eligible"
        if is_eligible:
            academic_status = "Eligible"

        completed_count = student.semester_performances.filter(semester__lt=student.semester, spi__isnull=False).count()
        current_year_str = "1st Year"
        if student.semester in [3, 4]:
            current_year_str = "2nd Year"
        elif student.semester in [5, 6]:
            current_year_str = "3rd Year"
        elif student.semester in [7, 8]:
            current_year_str = "4th Year"

        context = {
            **_base_ctx(request, student),
            'performances': performances,
            'min_required_cgpa': min_required_cgpa,
            'is_eligible': is_eligible,
            'academic_status': academic_status,
            'completed_count': completed_count,
            'current_year_str': current_year_str,
            'is_edit': True,
            'form': form,
        }
        return render(request, self.template_name, context)


# ─────────────────────────────────────────────────────────────────────────────
# Resume Upload
# ─────────────────────────────────────────────────────────────────────────────

class StudentResumeUploadView(StudentRequiredMixin, View):
    """Handles uploading a new Resume or CV, executing python extraction, and analyzing ATS score."""

    def post(self, request, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return redirect('accounts:logout')

        form = ResumeUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, err)
            return redirect('student_portal:resume_dashboard')

        resume_type = form.cleaned_data['resume_type']
        file = form.cleaned_data['file']

        # Determine version number
        latest = StudentResume.objects.filter(student=student, resume_type=resume_type).order_by('-version').first()
        version = (latest.version + 1) if latest else 1

        # Deactivate previous active version of this type
        StudentResume.objects.filter(student=student, resume_type=resume_type).update(is_active=False)

        # Create record
        new_resume = StudentResume(
            student=student,
            file=file,
            resume_type=resume_type,
            version=version,
            is_active=True
        )

        # Save temporarily to get file path on disk
        new_resume.save()

        # Execute text extraction & analysis using Python
        try:
            raw_text = extract_pdf_text(new_resume.file.path)
            analysis = analyze_resume_text(raw_text)

            new_resume.extracted_text = raw_text
            new_resume.ats_score = analysis['ats_score']
            new_resume.completion_score = analysis['completion_score']
            new_resume.formatting_score = analysis['formatting_score']

            # Serialize lists/suggestions to JSON strings
            new_resume.projects_found = json.dumps(analysis['projects_found'])
            new_resume.education_found = json.dumps(analysis['education_found'])
            new_resume.skills_found = json.dumps(analysis['skills_found'])
            new_resume.certificates_found = json.dumps(analysis['certificates_found'])
            new_resume.experience_found = json.dumps(analysis['experience_found'])
            new_resume.missing_keywords = json.dumps(analysis['missing_keywords'])
            new_resume.suggestions = json.dumps(analysis['suggestions'])
            new_resume.save()

            # Sync legacy student.resume field for compatibility if type is RESUME
            if resume_type == 'RESUME':
                student.resume = new_resume.file
                student.resume_uploaded_at = timezone.now()
                student.save()

            messages.success(request, f"{new_resume.get_resume_type_display()} v{new_resume.version} uploaded and analyzed successfully!")
        except Exception as e:
            messages.error(request, f"Error analyzing PDF content: {e}")

        return redirect('student_portal:resume_dashboard')


# ─────────────────────────────────────────────────────────────────────────────
# Placement Drives (Active, Upcoming, Closed, Bookmarks, Search, Filters)
# ─────────────────────────────────────────────────────────────────────────────

class StudentDrivesView(StudentRequiredMixin, View):
    template_name = 'student_portal/drives.html'

    def get(self, request, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return redirect('accounts:logout')

        tab = request.GET.get('tab', 'active').strip().lower()
        q = request.GET.get('q', '').strip()
        drive_type = request.GET.get('type', '').strip()

        # Base filter by college and created by college admin
        drives = PlacementDrive.objects.filter(college=student.college)

        # Tab filters
        if tab == 'upcoming':
            drives = drives.filter(status='UPCOMING')
        elif tab == 'closed':
            drives = drives.filter(status='COMPLETED')
        else:
            tab = 'active'
            drives = drives.filter(status='ACTIVE')

        # Search filter
        if q:
            drives = drives.filter(
                Q(role__icontains=q) | 
                Q(company__name__icontains=q) |
                Q(company__industry__icontains=q)
            )

        # Type filter
        if drive_type:
            drives = drives.filter(drive_type=drive_type)

        drives = drives.select_related('company').order_by('deadline')

        # Retrieve student's applications and bookmarks
        applied_drive_ids = set(
            Application.objects.filter(student=student).values_list('drive_id', flat=True)
        )
        bookmarked_drive_ids = set(
            DriveBookmark.objects.filter(student=student).values_list('drive_id', flat=True)
        )

        drives_data = []
        for d in drives:
            # Auto-calculate basic eligibility check
            eligible = True
            
            # CGPA check
            if student.cgpa is not None and student.cgpa < d.min_cgpa:
                eligible = False
            # Department check
            if d.eligible_departments.exists() and student.department not in d.eligible_departments.all():
                eligible = False
            # Batch check
            if d.eligible_batches.exists() and student.batch not in d.eligible_batches.all():
                eligible = False
            # Backlog check
            if student.backlogs > d.max_backlogs:
                eligible = False
            # Skill check (if specified)
            if d.required_skills:
                req_skills = [s.strip().lower() for s in d.required_skills.split(',') if s.strip()]
                student_skills = [s.name.lower() for s in student.skill_entries.all()] + [s.strip().lower() for s in student.skills.split(',') if s.strip()]
                if any(rs not in student_skills for rs in req_skills):
                    eligible = False

            drives_data.append({
                'drive': d,
                'eligible': eligible,
                'applied': d.pk in applied_drive_ids,
                'bookmarked': d.pk in bookmarked_drive_ids,
            })

        return render(request, self.template_name, {
            **_base_ctx(request, student),
            'drives_data': drives_data,
            'tab': tab,
            'q': q,
            'drive_type': drive_type,
            'applied_count': len(applied_drive_ids),
            'bookmark_count': len(bookmarked_drive_ids),
        })


class StudentDriveDetailView(StudentRequiredMixin, View):
    """Detailed view for a Placement Drive, checking eligibility criteria automatically."""
    template_name = 'student_portal/drive_detail.html'

    def get(self, request, pk, *args, **kwargs):
        student = _get_student(request)
        drive = get_object_or_404(PlacementDrive, pk=pk, college=student.college)

        # Eligibility checklist
        checklist = {
            'cgpa': {'name': 'CGPA Requirement', 'status': True, 'desc': f'Your CGPA: {student.cgpa or "N/A"} (Required: Min {drive.min_cgpa})'},
            'department': {'name': 'Department Eligibility', 'status': True, 'desc': f'Your Department: {student.department.name} (Eligible)'},
            'batch': {'name': 'Passing Batch', 'status': True, 'desc': f'Your Batch: {student.batch.name} (Eligible)'},
            'backlogs': {'name': 'Backlogs Limit', 'status': True, 'desc': f'Your Backlogs: {student.backlogs} (Allowed: Max {drive.max_backlogs})'},
            'skills': {'name': 'Required Skills', 'status': True, 'desc': 'All required skills matched'},
        }

        # 1. CGPA Check
        if student.cgpa is not None and student.cgpa < drive.min_cgpa:
            checklist['cgpa']['status'] = False
            checklist['cgpa']['desc'] = f'Your CGPA is {student.cgpa}, but a minimum of {drive.min_cgpa} is required.'
        elif student.cgpa is None:
            checklist['cgpa']['status'] = False
            checklist['cgpa']['desc'] = f'CGPA not defined on your profile. Required: Min {drive.min_cgpa}.'

        # 2. Department Check
        if drive.eligible_departments.exists() and student.department not in drive.eligible_departments.all():
            checklist['department']['status'] = False
            depts = ', '.join([d.code for d in drive.eligible_departments.all()])
            checklist['department']['desc'] = f'Eligible departments: {depts}. Your department is {student.department.code}.'

        # 3. Batch Check
        if drive.eligible_batches.exists() and student.batch not in drive.eligible_batches.all():
            checklist['batch']['status'] = False
            batches = ', '.join([b.name for b in drive.eligible_batches.all()])
            checklist['batch']['desc'] = f'Eligible batches: {batches}. Your batch is {student.batch.name}.'

        # 4. Backlogs Check
        if student.backlogs > drive.max_backlogs:
            checklist['backlogs']['status'] = False
            checklist['backlogs']['desc'] = f'You have {student.backlogs} active backlog(s). Maximum allowed: {drive.max_backlogs}.'

        # 5. Skills Check
        missing_skills = []
        if drive.required_skills:
            req_skills = [s.strip() for s in drive.required_skills.split(',') if s.strip()]
            student_skills = [s.name.lower() for s in student.skill_entries.all()] + [s.strip().lower() for s in student.skills.split(',') if s.strip()]
            for rs in req_skills:
                if rs.lower() not in student_skills:
                    missing_skills.append(rs)

            if missing_skills:
                checklist['skills']['status'] = False
                checklist['skills']['desc'] = f'Missing required skills: {", ".join(missing_skills)}.'

        # Decide overall eligibility
        is_eligible = all(item['status'] for item in checklist.values())

        # Check applied status
        application = Application.objects.filter(drive=drive, student=student).first()
        is_bookmarked = DriveBookmark.objects.filter(student=student, drive=drive).exists()

        return render(request, self.template_name, {
            **_base_ctx(request, student),
            'drive': drive,
            'checklist': checklist,
            'is_eligible': is_eligible,
            'application': application,
            'is_bookmarked': is_bookmarked,
        })


class StudentBookmarkToggleView(StudentRequiredMixin, View):
    """POST-only view to toggle bookmark for a placement drive."""
    def post(self, request, pk, *args, **kwargs):
        student = _get_student(request)
        drive = get_object_or_404(PlacementDrive, pk=pk, college=student.college)
        
        bookmark = DriveBookmark.objects.filter(student=student, drive=drive).first()
        if bookmark:
            bookmark.delete()
            messages.success(request, f"Removed bookmark for {drive.role} at {drive.company.name}.")
        else:
            DriveBookmark.objects.create(student=student, drive=drive)
            messages.success(request, f"Bookmarked {drive.role} at {drive.company.name}!")
            
        return redirect(request.META.get('HTTP_REFERER', 'student_portal:drives'))


class StudentApplyView(StudentRequiredMixin, View):
    """POST endpoint to apply for a placement drive, verifying eligibility and populating calendar."""
    def post(self, request, pk, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return redirect('accounts:logout')

        drive = get_object_or_404(PlacementDrive, pk=pk, college=student.college, status__in=['UPCOMING', 'ACTIVE'])

        # Check already applied
        if Application.objects.filter(drive=drive, student=student).exists():
            messages.warning(request, f"You have already applied to {drive.role} at {drive.company.name}.")
            return redirect('student_portal:drives')

        # Full eligibility criteria checks
        eligible = True
        
        if student.cgpa is not None and student.cgpa < drive.min_cgpa:
            eligible = False
        if drive.eligible_departments.exists() and student.department not in drive.eligible_departments.all():
            eligible = False
        if drive.eligible_batches.exists() and student.batch not in drive.eligible_batches.all():
            eligible = False
        if student.backlogs > drive.max_backlogs:
            eligible = False
        if drive.required_skills:
            req_skills = [s.strip().lower() for s in drive.required_skills.split(',') if s.strip()]
            student_skills = [s.name.lower() for s in student.skill_entries.all()] + [s.strip().lower() for s in student.skills.split(',') if s.strip()]
            if any(rs not in student_skills for rs in req_skills):
                eligible = False

        if not eligible:
            messages.error(request, "You do not meet the eligibility criteria for this drive.")
            return redirect('student_portal:drives')

        # Create application
        Application.objects.create(drive=drive, student=student, status='APPLIED')

        # Automatically populate Student Placement Calendar Events (6 specific types)
        today = timezone.localdate()
        
        # 1. Application Deadline
        deadline_date = drive.deadline if drive.deadline else (today + timezone.timedelta(days=4))
        PlacementCalendarEvent.objects.get_or_create(
            student=student,
            drive=drive,
            event_type='DEADLINE',
            defaults={
                'title': f"Application Deadline: {drive.company.name}",
                'description': f"Final date to submit applications for {drive.role}.",
                'event_date': deadline_date
            }
        )

        # 2. Aptitude Test
        PlacementCalendarEvent.objects.get_or_create(
            student=student,
            drive=drive,
            event_type='APTITUDE_TEST',
            defaults={
                'title': f"Aptitude Test: {drive.company.name}",
                'description': f"Structured numerical and logical testing round for {drive.role}.",
                'event_date': today + timezone.timedelta(days=2)
            }
        )

        # 3. Technical Interview
        PlacementCalendarEvent.objects.get_or_create(
            student=student,
            drive=drive,
            event_type='TECH_INTERVIEW',
            defaults={
                'title': f"Technical Interview: {drive.company.name}",
                'description': f"Technical rounds covering core concepts, DSA, and coding for {drive.role}.",
                'event_date': today + timezone.timedelta(days=5)
            }
        )

        # 4. HR Interview
        PlacementCalendarEvent.objects.get_or_create(
            student=student,
            drive=drive,
            event_type='HR_INTERVIEW',
            defaults={
                'title': f"HR Interview: {drive.company.name}",
                'description': f"Culture-fit, behavioral, and HR panel review for {drive.role}.",
                'event_date': today + timezone.timedelta(days=7)
            }
        )

        # 5. Offer Release
        PlacementCalendarEvent.objects.get_or_create(
            student=student,
            drive=drive,
            event_type='OFFER_RELEASE',
            defaults={
                'title': f"Offer Release: {drive.company.name}",
                'description': f"Declaration of selected candidates and offer letter release for {drive.role}.",
                'event_date': today + timezone.timedelta(days=9)
            }
        )

        # 6. Joining Date
        PlacementCalendarEvent.objects.get_or_create(
            student=student,
            drive=drive,
            event_type='JOINING_DATE',
            defaults={
                'title': f"Joining Date: {drive.company.name}",
                'description': f"Expected date of joining for the {drive.role} role.",
                'event_date': today + timezone.timedelta(days=30)
            }
        )

        messages.success(request, f"Successfully applied to {drive.role} at {drive.company.name}! Placement calendar updated.")
        return redirect('student_portal:applications')


# ─────────────────────────────────────────────────────────────────────────────
# Placement Calendar
# ─────────────────────────────────────────────────────────────────────────────

class StudentCalendarView(StudentRequiredMixin, View):
    """Displays placement drive timeline events for applied drives grouped by timeframe."""
    template_name = 'student_portal/calendar.html'

    def get(self, request, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return redirect('accounts:logout')

        # Retrieve the drive IDs the student has applied for
        applied_drive_ids = Application.objects.filter(student=student).values_list('drive_id', flat=True)

        # Filter events by applied drives ONLY
        events = PlacementCalendarEvent.objects.filter(
            student=student,
            drive_id__in=applied_drive_ids
        ).select_related('drive', 'drive__company').order_by('event_date')

        # Timeframe groupings based on current date
        today = timezone.localdate()
        tomorrow = today + timezone.timedelta(days=1)
        end_of_week = today + timezone.timedelta(days=7)

        today_events = events.filter(event_date=today)
        tomorrow_events = events.filter(event_date=tomorrow)
        this_week_events = events.filter(event_date__gt=tomorrow, event_date__lte=end_of_week)
        upcoming_events = events.filter(event_date__gt=end_of_week)

        return render(request, self.template_name, {
            **_base_ctx(request, student),
            'today_events': today_events,
            'tomorrow_events': tomorrow_events,
            'this_week_events': this_week_events,
            'upcoming_events': upcoming_events,
            'total_events': events.count(),
        })



# ─────────────────────────────────────────────────────────────────────────────
# Applications
# ─────────────────────────────────────────────────────────────────────────────

class StudentApplicationsView(StudentRequiredMixin, View):
    template_name = 'student_portal/applications.html'

    def get(self, request, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return redirect('accounts:logout')

        applications = Application.objects.filter(
            student=student
        ).select_related('drive', 'drive__company').order_by('-applied_at')

        status_filter = request.GET.get('status', '')
        if status_filter:
            applications = applications.filter(status=status_filter)

        return render(request, self.template_name, {
            **_base_ctx(request, student),
            'applications': applications,
            'status_filter': status_filter,
        })


# ─────────────────────────────────────────────────────────────────────────────
# Notifications
# ─────────────────────────────────────────────────────────────────────────────

class StudentNotificationsView(StudentRequiredMixin, View):
    template_name = 'student_portal/notifications.html'

    def get(self, request, *args, **kwargs):
        student = _get_student(request)
        notifications = Notification.objects.filter(user=request.user)
        return render(request, self.template_name, {
            **_base_ctx(request, student),
            'notifications': notifications,
            'unread_count': notifications.filter(is_read=False).count(),
        })


class StudentMarkNotificationReadView(StudentRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        notif = get_object_or_404(Notification, pk=pk, user=request.user)
        notif.is_read = True
        notif.save()
        return redirect('student_portal:notifications')


# ─────────────────────────────────────────────────────────────────────────────
# Settings
# ─────────────────────────────────────────────────────────────────────────────

class StudentSettingsView(StudentRequiredMixin, View):
    template_name = 'student_portal/settings.html'

    def get(self, request, *args, **kwargs):
        student = _get_student(request)
        return render(request, self.template_name, {**_base_ctx(request, student)})


# ─────────────────────────────────────────────────────────────────────────────
# Skills — List / Add / Edit / Delete
# ─────────────────────────────────────────────────────────────────────────────

class StudentSkillsView(StudentRequiredMixin, View):
    """Display all skills grouped by category, with summary stats."""
    template_name = 'student_portal/skills.html'

    def get(self, request, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return redirect('accounts:logout')

        all_skills = StudentSkill.objects.filter(student=student)

        # Group by category for section rendering
        categories = StudentSkill.Category.choices  # [(value, label), ...]
        grouped = {}
        for cat_value, cat_label in categories:
            skills_in_cat = all_skills.filter(category=cat_value)
            if skills_in_cat.exists():
                grouped[cat_value] = {
                    'label': cat_label,
                    'skills': skills_in_cat,
                    'icon': StudentSkill(category=cat_value).category_icon,
                }

        # Summary counts by proficiency
        beginner_count     = all_skills.filter(proficiency='BEGINNER').count()
        intermediate_count = all_skills.filter(proficiency='INTERMEDIATE').count()
        advanced_count     = all_skills.filter(proficiency='ADVANCED').count()

        # Category distribution for stat pills
        category_stats = []
        for cat_value, cat_label in categories:
            cnt = all_skills.filter(category=cat_value).count()
            if cnt:
                category_stats.append({'label': cat_label, 'count': cnt})

        form = StudentSkillForm()

        return render(request, self.template_name, {
            **_base_ctx(request, student),
            'all_skills':        all_skills,
            'grouped':           grouped,
            'total_skills':      all_skills.count(),
            'beginner_count':    beginner_count,
            'intermediate_count':intermediate_count,
            'advanced_count':    advanced_count,
            'category_stats':    category_stats,
            'form':              form,
            'categories':        StudentSkill.Category.choices,
            'proficiencies':     StudentSkill.Proficiency.choices,
        })


class StudentSkillAddView(StudentRequiredMixin, View):
    """POST-only: add a new skill for the logged-in student."""

    def post(self, request, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return redirect('accounts:logout')

        form = StudentSkillForm(request.POST)
        if form.is_valid():
            skill = form.save(commit=False)
            skill.student = student
            try:
                skill.save()
                messages.success(request, f'Skill "{skill.name}" added successfully!')
            except Exception:
                messages.error(request, f'Skill "{skill.name}" already exists in your list.')
        else:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, err)

        return redirect('student_portal:skills')


class StudentSkillEditView(StudentRequiredMixin, View):
    """GET shows pre-filled edit form; POST saves changes."""
    template_name = 'student_portal/skill_edit.html'

    def _get_skill(self, request, pk):
        student = _get_student(request)
        return get_object_or_404(StudentSkill, pk=pk, student=student)

    def get(self, request, pk, *args, **kwargs):
        skill   = self._get_skill(request, pk)
        student = skill.student
        form    = StudentSkillForm(instance=skill)
        return render(request, self.template_name, {
            **_base_ctx(request, student),
            'form':  form,
            'skill': skill,
        })

    def post(self, request, pk, *args, **kwargs):
        skill  = self._get_skill(request, pk)
        form   = StudentSkillForm(request.POST, instance=skill)
        if form.is_valid():
            form.save()
            messages.success(request, f'Skill "{skill.name}" updated.')
            return redirect('student_portal:skills')
        return render(request, self.template_name, {
            **_base_ctx(request, skill.student),
            'form':  form,
            'skill': skill,
        })


class StudentSkillDeleteView(StudentRequiredMixin, View):
    """POST-only: delete a skill (GET shows confirmation page)."""
    template_name = 'student_portal/skill_delete.html'

    def _get_skill(self, request, pk):
        student = _get_student(request)
        return get_object_or_404(StudentSkill, pk=pk, student=student)

    def get(self, request, pk, *args, **kwargs):
        skill   = self._get_skill(request, pk)
        return render(request, self.template_name, {
            **_base_ctx(request, skill.student),
            'skill': skill,
        })

    def post(self, request, pk, *args, **kwargs):
        skill = self._get_skill(request, pk)
        name  = skill.name
        skill.delete()
        messages.success(request, f'Skill "{name}" removed.')
        return redirect('student_portal:skills')


# ─────────────────────────────────────────────────────────────────────────────
# Resume & CV Dashboard views
# ─────────────────────────────────────────────────────────────────────────────

class StudentResumeDashboardView(StudentRequiredMixin, View):
    """Resume Management Dashboard: displaying active analysis & history."""
    template_name = 'student_portal/resume_dashboard.html'

    def get(self, request, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return redirect('accounts:logout')

        # Retrieve active versions
        active_resume = StudentResume.objects.filter(student=student, resume_type='RESUME', is_active=True).first()
        active_cv     = StudentResume.objects.filter(student=student, resume_type='CV', is_active=True).first()

        # Retrieve version list for comparison drop-downs and history table
        all_resumes = StudentResume.objects.filter(student=student).order_by('-uploaded_at')

        # Prepare JSON lists parsing for active resume/CV display
        resume_analysis = None
        if active_resume:
            resume_analysis = {
                'projects':     json.loads(active_resume.projects_found or '[]'),
                'education':    json.loads(active_resume.education_found or '[]'),
                'skills':       json.loads(active_resume.skills_found or '[]'),
                'certificates': json.loads(active_resume.certificates_found or '[]'),
                'experience':   json.loads(active_resume.experience_found or '[]'),
                'keywords':     json.loads(active_resume.missing_keywords or '[]'),
                'suggestions':  json.loads(active_resume.suggestions or '[]'),
            }

        cv_analysis = None
        if active_cv:
            cv_analysis = {
                'projects':     json.loads(active_cv.projects_found or '[]'),
                'education':    json.loads(active_cv.education_found or '[]'),
                'skills':       json.loads(active_cv.skills_found or '[]'),
                'certificates': json.loads(active_cv.certificates_found or '[]'),
                'experience':   json.loads(active_cv.experience_found or '[]'),
                'keywords':     json.loads(active_cv.missing_keywords or '[]'),
                'suggestions':  json.loads(active_cv.suggestions or '[]'),
            }

        form = ResumeUploadForm()

        return render(request, self.template_name, {
            **_base_ctx(request, student),
            'active_resume':    active_resume,
            'active_cv':        active_cv,
            'resume_analysis':  resume_analysis,
            'cv_analysis':      cv_analysis,
            'all_resumes':      all_resumes,
            'form':             form,
        })


class StudentResumeDownloadView(StudentRequiredMixin, View):
    """View to download a specific version of a student's resume/CV."""
    def get(self, request, pk, *args, **kwargs):
        student = _get_student(request)
        resume = get_object_or_404(StudentResume, pk=pk, student=student)
        
        # Serve file response
        from django.http import FileResponse
        response = FileResponse(resume.file.open(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{resume.filename}"'
        return response


class StudentResumeDeleteView(StudentRequiredMixin, View):
    """GET shows delete confirmation, POST performs deletion and updates active status."""
    template_name = 'student_portal/resume_delete.html'

    def get(self, request, pk, *args, **kwargs):
        student = _get_student(request)
        resume = get_object_or_404(StudentResume, pk=pk, student=student)
        return render(request, self.template_name, {
            **_base_ctx(request, student),
            'resume': resume
        })

    def post(self, request, pk, *args, **kwargs):
        student = _get_student(request)
        resume = get_object_or_404(StudentResume, pk=pk, student=student)
        
        resume_type = resume.resume_type
        is_active = resume.is_active
        filename = resume.filename
        
        # Delete file on disk & record
        try:
            resume.file.delete(save=False)
        except Exception:
            pass
        resume.delete()

        # If we deleted the active resume/CV, set the next newest available version as active
        if is_active:
            next_newest = StudentResume.objects.filter(student=student, resume_type=resume_type).order_by('-version').first()
            if next_newest:
                next_newest.is_active = True
                next_newest.save()
                
                # Sync legacy student.resume
                if resume_type == 'RESUME':
                    student.resume = next_newest.file
                    student.save()
            else:
                # No resumes left
                if resume_type == 'RESUME':
                    student.resume = None
                    student.save()

        messages.success(request, f'File "{filename}" deleted successfully.')
        return redirect('student_portal:resume_dashboard')


class StudentResumeCompareView(StudentRequiredMixin, View):
    """Allows side-by-side comparison of any two uploaded resume/CV versions."""
    template_name = 'student_portal/resume_compare.html'

    def get(self, request, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return redirect('accounts:logout')

        pk1 = request.GET.get('version1')
        pk2 = request.GET.get('version2')

        if not pk1 or not pk2:
            messages.warning(request, "Please select two versions to compare.")
            return redirect('student_portal:resume_dashboard')

        ver1 = get_object_or_404(StudentResume, pk=pk1, student=student)
        ver2 = get_object_or_404(StudentResume, pk=pk2, student=student)

        # Parse JSON detail fields for presentation
        analysis1 = {
            'projects':     json.loads(ver1.projects_found or '[]'),
            'education':    json.loads(ver1.education_found or '[]'),
            'skills':       json.loads(ver1.skills_found or '[]'),
            'certificates': json.loads(ver1.certificates_found or '[]'),
            'experience':   json.loads(ver1.experience_found or '[]'),
            'keywords':     json.loads(ver1.missing_keywords or '[]'),
            'suggestions':  json.loads(ver1.suggestions or '[]'),
        }

        analysis2 = {
            'projects':     json.loads(ver2.projects_found or '[]'),
            'education':    json.loads(ver2.education_found or '[]'),
            'skills':       json.loads(ver2.skills_found or '[]'),
            'certificates': json.loads(ver2.certificates_found or '[]'),
            'experience':   json.loads(ver2.experience_found or '[]'),
            'keywords':     json.loads(ver2.missing_keywords or '[]'),
            'suggestions':  json.loads(ver2.suggestions or '[]'),
        }

        return render(request, self.template_name, {
            **_base_ctx(request, student),
            'ver1': ver1,
            'ver2': ver2,
            'analysis1': analysis1,
            'analysis2': analysis2,
        })


# ─────────────────────────────────────────────────────────────────────────────
# Smart Recommendations View
# ─────────────────────────────────────────────────────────────────────────────

class StudentRecommendationsView(StudentRequiredMixin, View):
    """Generates smart jobs/internships/companies recommendations comparing skills, projects, and CGPA."""
    template_name = 'student_portal/recommendations.html'

    def get(self, request, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return redirect('accounts:logout')

        # 1. Gather all student skills
        student_skills = set()
        if student.skills:
            for s in student.skills.split(','):
                if s.strip():
                    student_skills.add(s.strip().lower())
        for se in student.skill_entries.all():
            student_skills.add(se.name.strip().lower())

        # 2. Extract active resume info (skills, projects, certificates)
        active_resume = student.resume_versions.filter(is_active=True).first()
        resume_skills_list = []
        projects_list = []
        certificates_list = []

        if active_resume:
            try:
                resume_skills_list = json.loads(active_resume.skills_found or '[]')
                for s in resume_skills_list:
                    student_skills.add(s.strip().lower())
            except Exception:
                pass
            try:
                projects_list = json.loads(active_resume.projects_found or '[]')
            except Exception:
                pass
            try:
                certificates_list = json.loads(active_resume.certificates_found or '[]')
            except Exception:
                pass

        # Helper strings for project & certificate searches
        projects_str = " ".join([str(p) for p in projects_list]).lower()
        certificates_str = " ".join([str(c) for c in certificates_list]).lower()

        # 3. Placement Drives Match (On-campus)
        placement_drives = PlacementDrive.objects.filter(
            college=student.college,
            status__in=['ACTIVE', 'UPCOMING']
        ).select_related('company')

        recommended_jobs_oncampus = []
        recommended_internships_oncampus = []

        for drive in placement_drives:
            matched_skills = []
            missing_skills = []
            reasons = []

            # Match skills
            req_skills = [s.strip() for s in drive.required_skills.split(',') if s.strip()]
            if req_skills:
                for rs in req_skills:
                    if rs.lower() in student_skills:
                        matched_skills.append(rs)
                    else:
                        missing_skills.append(rs)
                skill_match_ratio = len(matched_skills) / len(req_skills)
            else:
                skill_match_ratio = 1.0

            # Eligibility checklist details
            eligible_cgpa = student.cgpa is not None and student.cgpa >= drive.min_cgpa
            eligible_dept = not drive.eligible_departments.exists() or student.department in drive.eligible_departments.all()
            eligible_batch = not drive.eligible_batches.exists() or student.batch in drive.eligible_batches.all()
            eligible_backlogs = student.backlogs <= drive.max_backlogs

            # Calculate match score
            match_score = 50 + int(skill_match_ratio * 50)
            
            # Penalties for ineligibility
            if not eligible_cgpa:
                match_score -= 20
                reasons.append(f"Requires minimum CGPA of {drive.min_cgpa} (Your CGPA: {student.cgpa or 'N/A'}).")
            if not eligible_dept:
                match_score -= 15
                reasons.append("Your department is not listed in the eligible departments.")
            if not eligible_batch:
                match_score -= 15
                reasons.append("Your batch is not eligible for this drive.")
            if not eligible_backlogs:
                match_score -= 20
                reasons.append(f"Drive allows max {drive.max_backlogs} active backlog(s) (You have {student.backlogs}).")

            # Check if skills are highlighted in projects/certificates
            project_mentions = [s for s in matched_skills if s.lower() in projects_str]
            cert_mentions = [s for s in matched_skills if s.lower() in certificates_str]

            # Construct explainability reasons
            if eligible_cgpa and eligible_dept and eligible_batch and eligible_backlogs:
                reasons.append("You satisfy all core academic eligibility criteria (CGPA, Department, Batch, Backlogs).")
            
            if matched_skills:
                reasons.append(f"Matches your profile/resume skills: {', '.join(matched_skills)}.")
            
            if project_mentions:
                reasons.append(f"Matching skills validated in your resume projects: {', '.join(project_mentions)}.")
            if cert_mentions:
                reasons.append(f"Matching skills validated in your professional certificates: {', '.join(cert_mentions)}.")

            if missing_skills:
                reasons.append(f"Consider acquiring required skills to improve match: {', '.join(missing_skills)}.")

            match_score = max(min(match_score, 100), 0)

            rec_item = {
                'id': drive.pk,
                'role': drive.role,
                'company_name': drive.company.name,
                'industry': drive.company.industry or "Technology",
                'match_pct': match_score,
                'matched_skills': matched_skills,
                'missing_skills': missing_skills,
                'reasons': reasons,
                'source': 'ON-CAMPUS',
                'opportunity_url': reverse('student_portal:drive_detail', args=[drive.pk])
            }

            if drive.drive_type == 'JOB':
                recommended_jobs_oncampus.append(rec_item)
            else:
                recommended_internships_oncampus.append(rec_item)

        # 4. Scraped Opportunities Match (Off-campus)
        scraped_opps = ScrapedOpportunity.objects.filter(
            college=student.college
        ).exclude(verification_status='IGNORED')

        recommended_jobs_offcampus = []
        recommended_internships_offcampus = []
        recommended_companies_set = {}

        # Preset domain matching maps
        skill_domain_map = {
            'frontend': ['react', 'angular', 'vue', 'html', 'css', 'javascript', 'typescript', 'tailwind'],
            'backend': ['python', 'django', 'node', 'express', 'sql', 'postgresql', 'mongodb', 'api', 'flask'],
            'data': ['python', 'pandas', 'numpy', 'sql', 'machine learning', 'data science', 'tableau', 'powerbi'],
            'devops': ['aws', 'cloud', 'docker', 'kubernetes', 'jenkins', 'git', 'linux', 'ci/cd']
        }

        for opp in scraped_opps:
            matched_skills = []
            missing_skills = []
            reasons = []

            role_lower = opp.role.lower()

            # Find matching keywords in role title
            for skill in student_skills:
                if skill in role_lower:
                    matched_skills.append(skill.title())

            # Infer missing skills based on role category
            inferred_domain = None
            if any(k in role_lower for k in ['front', 'web', 'react', 'ui', 'css']):
                inferred_domain = 'frontend'
            elif any(k in role_lower for k in ['back', 'django', 'node', 'api', 'server']):
                inferred_domain = 'backend'
            elif any(k in role_lower for k in ['data', 'ml', 'analysis', 'ai', 'science']):
                inferred_domain = 'data'
            elif any(k in role_lower for k in ['devops', 'cloud', 'aws', 'docker', 'infrastructure']):
                inferred_domain = 'devops'

            if inferred_domain:
                domain_skills = skill_domain_map[inferred_domain]
                for ds in domain_skills:
                    if ds not in student_skills:
                        missing_skills.append(ds.title())

            # Calculate match %
            match_score = 55 + (len(matched_skills) * 15)
            if student.cgpa and student.cgpa > 8.0:
                match_score += 5  # high CGPA bonus
            
            match_score = min(match_score, 95)

            # Construct reasons
            if matched_skills:
                reasons.append(f"Identified matching skills in role title: {', '.join(matched_skills)}.")
            if inferred_domain:
                reasons.append(f"Role categorized as {inferred_domain.upper()} domain based on title analysis.")
                if missing_skills:
                    reasons.append(f"Popular skills for this domain to consider: {', '.join(missing_skills[:3])}.")
            else:
                reasons.append("Generic off-campus engineering match based on college profile validation.")

            if student.cgpa and student.cgpa > 8.0:
                reasons.append(f"Includes match bonus for your excellent CGPA of {student.cgpa}.")

            rec_item = {
                'id': opp.pk,
                'role': opp.role,
                'company_name': opp.company_name,
                'industry': "Information Technology",
                'match_pct': match_score,
                'matched_skills': matched_skills,
                'missing_skills': missing_skills,
                'reasons': reasons,
                'source': 'OFF-CAMPUS',
                'opportunity_url': opp.source or '#'
            }

            # Classify internship vs job
            is_intern = any(k in role_lower for k in ['intern', 'stipend', 'co-op'])
            if is_intern:
                recommended_internships_offcampus.append(rec_item)
            else:
                recommended_jobs_offcampus.append(rec_item)

            # Populate recommended companies aggregate
            comp_name = opp.company_name
            if comp_name not in recommended_companies_set:
                recommended_companies_set[comp_name] = {
                    'name': comp_name,
                    'location': opp.location or "Off-campus / Remote",
                    'match_pct': match_score,
                    'reasons': [f"Matches scraped off-campus role '{opp.role}'."]
                }
            else:
                if match_score > recommended_companies_set[comp_name]['match_pct']:
                    recommended_companies_set[comp_name]['match_pct'] = match_score

        # Also insert on-campus companies into companies aggregate
        for drive in placement_drives:
            cname = drive.company.name
            if cname not in recommended_companies_set:
                recommended_companies_set[cname] = {
                    'name': cname,
                    'location': drive.company.location or "On-Campus",
                    'match_pct': 70,
                    'reasons': [f"Active on-campus placement drive for '{drive.role}'."]
                }

        # Combine, sort and limit
        recommended_jobs = sorted(
            recommended_jobs_oncampus + recommended_jobs_offcampus,
            key=lambda x: x['match_pct'],
            reverse=True
        )[:8]

        recommended_internships = sorted(
            recommended_internships_oncampus + recommended_internships_offcampus,
            key=lambda x: x['match_pct'],
            reverse=True
        )[:8]

        recommended_companies = sorted(
            recommended_companies_set.values(),
            key=lambda x: x['match_pct'],
            reverse=True
        )[:8]

        return render(request, self.template_name, {
            **_base_ctx(request, student),
            'recommended_jobs': recommended_jobs,
            'recommended_internships': recommended_internships,
            'recommended_companies': recommended_companies,
            'total_jobs_count': len(recommended_jobs),
            'total_interns_count': len(recommended_internships),
            'total_companies_count': len(recommended_companies),
        })


# ─────────────────────────────────────────────────────────────────────────────
# Career Analytics & Passport PDF View
# ─────────────────────────────────────────────────────────────────────────────

class StudentAnalyticsView(StudentRequiredMixin, View):
    """Displays student career analytics, scores, readiness gauges, application statistics, and salary predictions."""
    template_name = 'student_portal/analytics.html'

    def get(self, request, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return redirect('accounts:logout')

        applications = Application.objects.filter(student=student).select_related('drive', 'drive__company')
        
        # Calculate stats
        total_apps = applications.count()
        total_interviews = applications.filter(status='SHORTLISTED').count()
        total_offers = applications.filter(status='SELECTED').count()

        # Gather scores
        ats_score = student.ats_score()
        readiness_score = student.placement_readiness()
        improvement_score = student.career_score()
        completion_score = student.profile_completion()

        # Compute dynamic Placement Probability
        cgpa_val = float(student.cgpa or 0)
        has_resume = 1 if student.resume else 0
        
        prob_score = (cgpa_val / 10.0 * 35) + (has_resume * 15) + (ats_score / 100.0 * 15) + (completion_score / 100.0 * 15) + (min(total_interviews * 5, 20))
        prob_score = round(min(max(prob_score, 0), 100))

        # Skill metrics count
        student_skills = set()
        if student.skills:
            for s in student.skills.split(','):
                if s.strip():
                    student_skills.add(s.strip().lower())
        for se in student.skill_entries.all():
            student_skills.add(se.name.strip().lower())
            
        active_resume = student.resume_versions.filter(is_active=True).first()
        if active_resume:
            try:
                r_skills = json.loads(active_resume.skills_found or '[]')
                for s in r_skills:
                    student_skills.add(s.strip().lower())
            except Exception:
                pass

        total_skills = len(student_skills)

        # ─── SALARY PREDICTION MATRIX ───
        # Base fresher package from CGPA (minimum 5.0 LPA baseline)
        cgpa_pred_val = float(student.cgpa or 6.5)
        base_salary = round(max(cgpa_pred_val * 0.8, 5.0), 2)

        skill_premiums = {
            'cloud': {
                'keywords': ['aws', 'cloud', 'gcp', 'azure', 'docker', 'kubernetes', 'jenkins', 'devops', 'ci/cd'],
                'amount': 1.5,
                'max_limit': 4.0,
                'label': 'Cloud & DevOps'
            },
            'languages': {
                'keywords': ['python', 'java', 'go', 'golang', 'c++', 'rust', 'ruby', 'swift', 'typescript'],
                'amount': 1.0,
                'max_limit': 3.0,
                'label': 'Programming Languages'
            },
            'frameworks': {
                'keywords': ['django', 'react', 'node', 'express', 'angular', 'vue', 'spring', 'flask', 'laravel'],
                'amount': 1.2,
                'max_limit': 3.0,
                'label': 'Frameworks'
            },
            'databases': {
                'keywords': ['sql', 'postgresql', 'mongodb', 'mysql', 'oracle', 'redis', 'cassandra', 'database'],
                'amount': 0.8,
                'max_limit': 2.0,
                'label': 'Databases'
            },
            'data_science': {
                'keywords': ['machine learning', 'deep learning', 'pandas', 'numpy', 'tensorflow', 'pytorch', 'scikit-learn', 'data science', 'ai'],
                'amount': 1.5,
                'max_limit': 4.0,
                'label': 'Data Science & AI'
            }
        }

        total_premium = 0.0
        applied_premiums = []

        for key, config in skill_premiums.items():
            matched_in_category = []
            for skill in student_skills:
                if skill in config['keywords']:
                    matched_in_category.append(skill.title())
            
            if matched_in_category:
                earned = len(matched_in_category) * config['amount']
                earned = min(earned, config['max_limit'])
                total_premium += earned
                applied_premiums.append({
                    'category': config['label'],
                    'matched': matched_in_category,
                    'earned': round(earned, 2)
                })

        predicted_salary = base_salary + total_premium
        predicted_min = round(max(predicted_salary - 0.75, 4.5), 2)
        predicted_max = round(predicted_salary + 1.25, 2)

        return render(request, self.template_name, {
            **_base_ctx(request, student),
            'ats_score': ats_score,
            'readiness_score': readiness_score,
            'improvement_score': improvement_score,
            'completion_score': completion_score,
            'total_apps': total_apps,
            'total_interviews': total_interviews,
            'total_offers': total_offers,
            'placement_probability': prob_score,
            'total_skills': total_skills,
            'applications': applications[:5],
            
            # Salary Prediction details
            'salary_min': predicted_min,
            'salary_max': predicted_max,
            'base_salary': base_salary,
            'applied_premiums': applied_premiums,
            'total_premium': round(total_premium, 2)
        })


class StudentCareerPassportPdfView(StudentRequiredMixin, View):
    """Generates a professional recruiter-friendly Career Passport PDF using ReportLab."""
    def get(self, request, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return redirect('accounts:logout')

        import io
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40
        )

        story = []
        styles = getSampleStyleSheet()

        # Custom paragraph styles
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=24,
            leading=28,
            textColor=colors.HexColor('#1e3a8a'),
            spaceAfter=4
        )
        subtitle_style = ParagraphStyle(
            'DocSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=11,
            leading=14,
            textColor=colors.HexColor('#4b5563'),
            spaceAfter=15
        )
        section_heading = ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=16,
            textColor=colors.HexColor('#111827'),
            spaceBefore=14,
            spaceAfter=6,
            keepWithNext=True
        )
        body_text = ParagraphStyle(
            'BodyTextCustom',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor('#374151')
        )
        meta_label = ParagraphStyle(
            'MetaLabel',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor('#1f2937')
        )

        # 1. Header Information
        story.append(Paragraph(student.name, title_style))
        contact_info = f"Roll No: {student.roll_number} | Email: {student.email} | Phone: {student.phone or 'N/A'}"
        story.append(Paragraph(contact_info, subtitle_style))

        # Bio Section
        if student.bio:
            story.append(Paragraph("<b>Professional Summary</b>", section_heading))
            story.append(Paragraph(student.bio, body_text))
            story.append(Spacer(1, 10))

        # 2. Academic Summary Table
        story.append(Paragraph("<b>Academic Details</b>", section_heading))
        academics_data = [
            [
                Paragraph("<b>Department:</b>", meta_label), Paragraph(student.department.name, body_text),
                Paragraph("<b>Batch:</b>", meta_label), Paragraph(student.batch.name, body_text)
            ],
            [
                Paragraph("<b>Current Semester:</b>", meta_label), Paragraph(str(student.semester), body_text),
                Paragraph("<b>CGPA / SPI / CPI:</b>", meta_label), Paragraph(f"{student.cgpa or 'N/A'} / {student.spi or 'N/A'} / {student.cpi or 'N/A'}", body_text)
            ],
            [
                Paragraph("<b>Division:</b>", meta_label), Paragraph(student.division or 'N/A', body_text),
                Paragraph("<b>Active Backlogs:</b>", meta_label), Paragraph(str(student.backlogs), body_text)
            ]
        ]
        academics_table = Table(academics_data, colWidths=[120, 150, 110, 150])
        academics_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f9fafb')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 6),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#e5e7eb')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#f3f4f6')),
        ]))
        story.append(academics_table)
        story.append(Spacer(1, 12))

        # 3. Career Scores Overview
        story.append(Paragraph("<b>Career Scores & Preparedness</b>", section_heading))
        scores_data = [
            [
                Paragraph("<b>ATS Score:</b>", meta_label), Paragraph(f"{student.ats_score()}%", body_text),
                Paragraph("<b>Placement Readiness:</b>", meta_label), Paragraph(f"{student.placement_readiness()}%", body_text)
            ],
            [
                Paragraph("<b>Profile Completion:</b>", meta_label), Paragraph(f"{student.profile_completion()}%", body_text),
                Paragraph("<b>Career Improvement:</b>", meta_label), Paragraph(f"{student.career_score()}%", body_text)
            ]
        ]
        scores_table = Table(scores_data, colWidths=[120, 150, 110, 150])
        scores_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f9fafb')),
            ('PADDING', (0,0), (-1,-1), 6),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#e5e7eb')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#f3f4f6')),
        ]))
        story.append(scores_table)
        story.append(Spacer(1, 12))

        # 4. Resume & Skills info
        active_resume = student.resume_versions.filter(is_active=True).first()
        student_skills = []
        if student.skills:
            student_skills = [s.strip() for s in student.skills.split(',') if s.strip()]
        for se in student.skill_entries.all():
            if se.name not in student_skills:
                student_skills.append(se.name)

        if active_resume:
            try:
                r_skills = json.loads(active_resume.skills_found or '[]')
                for s in r_skills:
                    if s not in student_skills:
                        student_skills.append(s)
            except Exception:
                pass

        story.append(Paragraph("<b>Skills Inventory</b>", section_heading))
        skills_text = ", ".join(student_skills) if student_skills else "No skills listed."
        story.append(Paragraph(skills_text, body_text))
        story.append(Spacer(1, 10))

        # Projects and Certificates (Parsed from Resume Analysis)
        if active_resume:
            try:
                projects = json.loads(active_resume.projects_found or '[]')
                if projects:
                    story.append(Paragraph("<b>Highlighted Projects</b>", section_heading))
                    for proj in projects:
                        story.append(Paragraph(f"• {proj}", body_text))
                    story.append(Spacer(1, 10))
            except Exception:
                pass

            try:
                certs = json.loads(active_resume.certificates_found or '[]')
                if certs:
                    story.append(Paragraph("<b>Professional Certificates</b>", section_heading))
                    for cert in certs:
                        story.append(Paragraph(f"• {cert}", body_text))
                    story.append(Spacer(1, 10))
            except Exception:
                pass

        # 5. Coding Profiles
        story.append(Paragraph("<b>Professional Profiles & Portfolios</b>", section_heading))
        profiles_data = [
            [Paragraph("<b>LinkedIn:</b>", meta_label), Paragraph(student.linkedin_url or 'N/A', body_text)],
            [Paragraph("<b>GitHub:</b>", meta_label), Paragraph(student.github_url or 'N/A', body_text)],
            [Paragraph("<b>Portfolio:</b>", meta_label), Paragraph(student.portfolio_url or 'N/A', body_text)]
        ]
        profiles_table = Table(profiles_data, colWidths=[120, 410])
        profiles_table.setStyle(TableStyle([
            ('PADDING', (0,0), (-1,-1), 4),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#e5e7eb')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#f3f4f6')),
        ]))
        story.append(profiles_table)
        story.append(Spacer(1, 12))

        # 6. Placement Application History
        apps = Application.objects.filter(student=student).select_related('drive', 'drive__company').order_by('-applied_at')
        if apps.exists():
            story.append(Paragraph("<b>Application History</b>", section_heading))
            app_table_data = [[
                Paragraph("<b>Company</b>", meta_label),
                Paragraph("<b>Role</b>", meta_label),
                Paragraph("<b>Date Applied</b>", meta_label),
                Paragraph("<b>Status</b>", meta_label)
            ]]
            for app in apps:
                app_table_data.append([
                    Paragraph(app.drive.company.name, body_text),
                    Paragraph(app.drive.role, body_text),
                    Paragraph(app.applied_at.strftime('%b %d, %Y'), body_text),
                    Paragraph(app.get_status_display(), body_text)
                ])

            app_table = Table(app_table_data, colWidths=[150, 160, 110, 110])
            app_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f3f4f6')),
                ('PADDING', (0,0), (-1,-1), 6),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e5e7eb')),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f9fafb')])
            ]))
            story.append(KeepTogether(app_table))

        doc.build(story)
        buffer.seek(0)
        
        filename = f"Career_Passport_{student.roll_number}.pdf"
        return FileResponse(buffer, as_attachment=True, filename=filename, content_type='application/pdf')


# ─────────────────────────────────────────────────────────────────────────────
# Project Portfolio Views
# ─────────────────────────────────────────────────────────────────────────────

class StudentProjectsListView(StudentRequiredMixin, View):
    template_name = 'student_portal/projects_list.html'

    def get(self, request, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return redirect('accounts:logout')

        # Base projects query
        projects = Project.objects.filter(student=student)

        # GET Search & Filter arguments
        q = request.GET.get('q', '').strip()
        category = request.GET.get('category', '').strip()
        status = request.GET.get('status', '').strip()

        if q:
            projects = projects.filter(
                Q(title__icontains=q) |
                Q(technologies__icontains=q) |
                Q(short_description__icontains=q)
            )
        if category:
            projects = projects.filter(category=category)
        if status:
            projects = projects.filter(status=status)

        # Pre-order: featured first, then created date descending
        projects = projects.order_by('-is_featured', '-created_at')

        # Stats calculations
        total_projects = Project.objects.filter(student=student).count()
        completed_projects = Project.objects.filter(student=student, status='COMPLETED').count()
        ongoing_projects = Project.objects.filter(student=student, status='ONGOING').count()
        featured_projects = Project.objects.filter(student=student, is_featured=True).count()
        
        # Portfolio Score: Average score of all projects
        avg_score = 0
        all_student_projects = Project.objects.filter(student=student)
        if all_student_projects.exists():
            avg_score = round(sum(p.portfolio_score for p in all_student_projects) / all_student_projects.count())

        recent_project = all_student_projects.order_by('-created_at').first()

        context = {
            **_base_ctx(request, student),
            'projects': projects,
            'total_projects': total_projects,
            'completed_projects': completed_projects,
            'ongoing_projects': ongoing_projects,
            'featured_projects': featured_projects,
            'portfolio_score': avg_score,
            'recent_project': recent_project,
            'categories': Project.Category.choices,
            'statuses': Project.Status.choices,
            'q': q,
            'selected_category': category,
            'selected_status': status,
        }
        return render(request, self.template_name, context)


class StudentProjectCreateView(StudentRequiredMixin, View):
    template_name = 'student_portal/project_form.html'

    def get(self, request, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return redirect('accounts:logout')
        form = ProjectForm()
        return render(request, self.template_name, {
            **_base_ctx(request, student),
            'form': form,
            'is_edit': False,
        })

    def post(self, request, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return redirect('accounts:logout')

        form = ProjectForm(request.POST, request.FILES)
        if form.is_valid():
            project = form.save(commit=False)
            project.student = student
            # If marked as featured, optionally unfeature other projects of this student
            if project.is_featured:
                Project.objects.filter(student=student, is_featured=True).update(is_featured=False)
            project.save()
            messages.success(request, f"Project '{project.title}' added successfully.")
            return redirect('student_portal:projects_list')
        
        return render(request, self.template_name, {
            **_base_ctx(request, student),
            'form': form,
            'is_edit': False,
        })


class StudentProjectUpdateView(StudentRequiredMixin, View):
    template_name = 'student_portal/project_form.html'

    def get(self, request, pk, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return redirect('accounts:logout')

        project = get_object_or_404(Project, pk=pk, student=student)
        form = ProjectForm(instance=project)
        return render(request, self.template_name, {
            **_base_ctx(request, student),
            'form': form,
            'project': project,
            'is_edit': True,
        })

    def post(self, request, pk, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return redirect('accounts:logout')

        project = get_object_or_404(Project, pk=pk, student=student)
        form = ProjectForm(request.POST, request.FILES, instance=project)
        if form.is_valid():
            updated_project = form.save(commit=False)
            # If marked as featured, unfeature other projects of this student
            if updated_project.is_featured:
                Project.objects.filter(student=student, is_featured=True).exclude(pk=project.pk).update(is_featured=False)
            updated_project.save()
            messages.success(request, f"Project '{updated_project.title}' updated successfully.")
            return redirect('student_portal:projects_list')

        return render(request, self.template_name, {
            **_base_ctx(request, student),
            'form': form,
            'project': project,
            'is_edit': True,
        })


class StudentProjectDeleteView(StudentRequiredMixin, View):
    template_name = 'student_portal/project_confirm_delete.html'

    def get(self, request, pk, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return redirect('accounts:logout')

        project = get_object_or_404(Project, pk=pk, student=student)
        return render(request, self.template_name, {
            **_base_ctx(request, student),
            'project': project,
        })

    def post(self, request, pk, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return redirect('accounts:logout')

        project = get_object_or_404(Project, pk=pk, student=student)
        title = project.title
        project.delete()
        messages.success(request, f"Project '{title}' has been deleted.")
        return redirect('student_portal:projects_list')


class StudentProjectDetailView(StudentRequiredMixin, View):
    template_name = 'student_portal/project_detail.html'

    def get(self, request, pk, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return redirect('accounts:logout')

        project = get_object_or_404(Project, pk=pk, student=student)
        
        # Portfolio Score breakdown check
        score_breakdown = {
            'github_completed': bool(project.github_url),
            'live_completed': bool(project.live_url),
            'doc_completed': bool(project.documentation_url),
            'desc_completed': bool(project.detailed_description and len(project.detailed_description.strip()) > 0),
            'tech_completed': len(project.technology_list) >= 5,
            'video_completed': bool(project.youtube_url),
            'featured_completed': project.is_featured,
        }

        context = {
            **_base_ctx(request, student),
            'project': project,
            'score_breakdown': score_breakdown,
            'is_recruiter': False,
        }
        return render(request, self.template_name, context)


class RecruiterPortfolioView(LoginRequiredMixin, View):
    template_name = 'student_portal/projects_list.html'

    def get(self, request, student_id, *args, **kwargs):
        # Allow any authenticated user (e.g. COLLEGE_ADMIN, Recruiters)
        student = get_object_or_404(Student, pk=student_id)
        
        # Recruiter view: show projects list of student, read-only
        projects = Project.objects.filter(student=student).order_by('-is_featured', '-created_at')

        # GET Search & Filter arguments
        q = request.GET.get('q', '').strip()
        category = request.GET.get('category', '').strip()
        status = request.GET.get('status', '').strip()

        if q:
            projects = projects.filter(
                Q(title__icontains=q) |
                Q(technologies__icontains=q) |
                Q(short_description__icontains=q)
            )
        if category:
            projects = projects.filter(category=category)
        if status:
            projects = projects.filter(status=status)

        total_projects = projects.count()
        completed_projects = projects.filter(status='COMPLETED').count()
        ongoing_projects = projects.filter(status='ONGOING').count()
        featured_projects = projects.filter(is_featured=True).count()
        
        avg_score = 0
        all_student_projects = Project.objects.filter(student=student)
        if all_student_projects.exists():
            avg_score = round(sum(p.portfolio_score for p in all_student_projects) / all_student_projects.count())

        recent_project = all_student_projects.order_by('-created_at').first()

        context = {
            'student': student,
            'projects': projects,
            'total_projects': total_projects,
            'completed_projects': completed_projects,
            'ongoing_projects': ongoing_projects,
            'featured_projects': featured_projects,
            'portfolio_score': avg_score,
            'recent_project': recent_project,
            'categories': Project.Category.choices,
            'statuses': Project.Status.choices,
            'q': q,
            'selected_category': category,
            'selected_status': status,
            'is_recruiter': True,
        }
        return render(request, self.template_name, context)


class RecruiterProjectDetailView(LoginRequiredMixin, View):
    template_name = 'student_portal/project_detail.html'

    def get(self, request, pk, *args, **kwargs):
        project = get_object_or_404(Project, pk=pk)
        
        # Portfolio Score breakdown check
        score_breakdown = {
            'github_completed': bool(project.github_url),
            'live_completed': bool(project.live_url),
            'doc_completed': bool(project.documentation_url),
            'desc_completed': bool(project.detailed_description and len(project.detailed_description.strip()) > 0),
            'tech_completed': len(project.technology_list) >= 5,
            'video_completed': bool(project.youtube_url),
            'featured_completed': project.is_featured,
        }

        context = {
            'student': project.student,
            'project': project,
            'score_breakdown': score_breakdown,
            'is_recruiter': True,
        }
        return render(request, self.template_name, context)


# ─────────────────────────────────────────────────────────────────────────────
# Developer Journey Helper Functions & Views
# ─────────────────────────────────────────────────────────────────────────────

def _get_journey_stats(student):
    today = datetime.date.today()
    this_year = today.year

    # Fetch unique dates of activities
    active_dates_qs = Activity.objects.filter(student=student).values_list('date', flat=True).distinct().order_by('-date')
    active_dates = sorted(list(set(active_dates_qs)), reverse=True)

    # Current Streak
    current_streak = 0
    if active_dates:
        if active_dates[0] == today or active_dates[0] == today - datetime.timedelta(days=1):
            current_streak = 1
            curr_date = active_dates[0]
            for next_date in active_dates[1:]:
                if curr_date - next_date == datetime.timedelta(days=1):
                    current_streak += 1
                    curr_date = next_date
                else:
                    break

    # Longest Streak
    longest_streak = 0
    if active_dates:
        asc_dates = sorted(active_dates)
        temp_streak = 1
        longest_streak = 1
        for i in range(1, len(asc_dates)):
            if asc_dates[i] - asc_dates[i-1] == datetime.timedelta(days=1):
                temp_streak += 1
            elif asc_dates[i] != asc_dates[i-1]:
                longest_streak = max(longest_streak, temp_streak)
                temp_streak = 1
        longest_streak = max(longest_streak, temp_streak)

    # Consistency Score (Active days in last 30 days)
    thirty_days_ago = today - datetime.timedelta(days=30)
    active_days_last_30 = Activity.objects.filter(
        student=student,
        date__range=[thirty_days_ago, today]
    ).values('date').distinct().count()
    consistency_score = min(100, round((active_days_last_30 / 30.0) * 100))

    # General Stats
    activities_this_year = Activity.objects.filter(student=student, date__year=this_year).count()
    weekly_updates = WeeklySummary.objects.filter(student=student, date__year=this_year).count()
    monthly_updates = MonthlySummary.objects.filter(student=student, date__year=this_year).count()
    hackathons_count = HackathonJournal.objects.filter(student=student).count()
    
    # Calculate learning hours
    learning_hours_val = Activity.objects.filter(
        student=student,
        category__in=['LEARNING', 'CODING_PRACTICE', 'WORKSHOP']
    ).aggregate(total=Sum('hours_spent'))['total'] or 0
    learning_hours = float(learning_hours_val)

    # Problems solved
    problems_solved = CodingPractice.objects.filter(student=student).aggregate(total=Sum('problems_solved'))['total'] or 0
    
    # Milestones
    milestones_count = ProjectMilestone.objects.filter(student=student).count()

    # Goals completed
    goals_completed = LearningGoal.objects.filter(student=student, status='COMPLETED').count()

    # Points & Growth Level
    points = (Activity.objects.filter(student=student).count() * 5) + (learning_hours * 2) + (problems_solved * 1) + (hackathons_count * 20) + (milestones_count * 10) + (goals_completed * 15)
    
    if points <= 50:
        level = "🌱 Beginner"
    elif points <= 150:
        level = "🌿 Consistent Learner"
    elif points <= 300:
        level = "🌳 Active Developer"
    elif points <= 500:
        level = "🚀 Placement Ready"
    else:
        level = "👑 Industry Ready"

    return {
        'current_streak': current_streak,
        'longest_streak': longest_streak,
        'consistency_score': consistency_score,
        'activities_this_year': activities_this_year,
        'weekly_updates': weekly_updates,
        'monthly_updates': monthly_updates,
        'hackathons_count': hackathons_count,
        'learning_hours': learning_hours,
        'problems_solved': problems_solved,
        'milestones_count': milestones_count,
        'goals_completed': goals_completed,
        'points': points,
        'growth_level': level
    }


def _get_available_years(student):
    """Return a descending list of calendar years that have at least one
    activity, always including the current year even if it has none yet."""
    years = {d.year for d in Activity.objects.filter(student=student).dates('date', 'year')}
    years.add(datetime.date.today().year)
    return sorted(years, reverse=True)


def _resolve_selected_year(request, available_years):
    """Read ?year= from the request and make sure it's a valid choice."""
    current_year = datetime.date.today().year
    try:
        selected_year = int(request.GET.get('year', current_year))
    except (TypeError, ValueError):
        selected_year = current_year
    if selected_year not in available_years:
        selected_year = current_year if current_year in available_years else available_years[0]
    return selected_year


def _get_heatmap_cols(student, year):
    start_date = datetime.date(year, 1, 1)
    weekday = start_date.weekday()
    if weekday < 6:
        start_date -= datetime.timedelta(days=weekday + 1)
    
    end_date = datetime.date(year, 12, 31)
    end_weekday = end_date.weekday()
    if end_weekday < 5:
        end_date += datetime.timedelta(days=5 - end_weekday)
    elif end_weekday == 6:
        end_date += datetime.timedelta(days=6)

    from django.db.models import Count
    activity_counts = Activity.objects.filter(
        student=student,
        date__year=year
    ).values('date').annotate(count=Count('id'))
    counts_dict = {item['date']: item['count'] for item in activity_counts}

    columns = []
    curr = start_date
    while curr <= end_date:
        col_days = []
        for _ in range(7):
            count = counts_dict.get(curr, 0)
            if count == 0:
                color = 'rgba(255, 255, 255, 0.05)'
            elif count <= 2:
                color = '#4c1d95'
            elif count <= 4:
                color = '#6d28d9'
            elif count <= 6:
                color = '#8b5cf6'
            else:
                color = '#c4b5fd'
            col_days.append({
                'date': curr,
                'count': count,
                'color': color,
                'is_current_year': curr.year == year,
            })
            curr += datetime.timedelta(days=1)
        columns.append(col_days)
    return columns


class DeveloperJourneyListView(StudentRequiredMixin, View):
    template_name = 'student_portal/journey_list.html'

    def get(self, request, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return redirect('accounts:logout')

        available_years = _get_available_years(student)
        selected_year = _resolve_selected_year(request, available_years)

        heatmap_cols = _get_heatmap_cols(student, selected_year)
        selected_year_activity_count = Activity.objects.filter(
            student=student, date__year=selected_year
        ).count()

        date_str = request.GET.get('date', '').strip()
        category_filter = request.GET.get('category', '').strip()

        activities = Activity.objects.filter(student=student)

        if date_str:
            try:
                clicked_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                activities = activities.filter(date=clicked_date)
            except ValueError:
                pass

        if category_filter:
            activities = activities.filter(category=category_filter)

        links, created = TechnicalLinks.objects.get_or_create(student=student)
        goals = LearningGoal.objects.filter(student=student)
        achievements = DeveloperAchievement.objects.filter(student=student)

        stats = _get_journey_stats(student)

        context = {
            **_base_ctx(request, student),
            'heatmap_cols': heatmap_cols,
            'activities': activities,
            'links': links,
            'goals': goals,
            'achievements': achievements,
            'date_filter': date_str,
            'category_filter': category_filter,
            'available_years': available_years,
            'selected_year': selected_year,
            'selected_year_activity_count': selected_year_activity_count,
            'categories': Activity.Category.choices,
            'is_recruiter': False,
            **stats
        }
        return render(request, self.template_name, context)


FORM_MAP = {
    'daily_log': (ActivityForm, Activity),
    'weekly_summary': (WeeklySummaryForm, WeeklySummary),
    'monthly_summary': (MonthlySummaryForm, MonthlySummary),
    'project_milestone': (ProjectMilestoneForm, ProjectMilestone),
    'hackathon': (HackathonJournalForm, HackathonJournal),
    'coding_practice': (CodingPracticeForm, CodingPractice),
    'learning_journal': (LearningJournalForm, LearningJournal),
    'open_source': (OpenSourceContributionForm, OpenSourceContribution),
    'goal': (LearningGoalForm, LearningGoal),
    'achievement': (DeveloperAchievementForm, DeveloperAchievement),
}


class AddJourneyActivityView(StudentRequiredMixin, View):
    template_name = 'student_portal/journey_form.html'

    def get(self, request, activity_type, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return redirect('accounts:logout')

        if activity_type not in FORM_MAP:
            messages.error(request, "Invalid activity type.")
            return redirect('student_portal:journey')

        form_class, model_class = FORM_MAP[activity_type]
        
        if activity_type == 'project_milestone':
            form = form_class(student=student)
        else:
            form = form_class()

        return render(request, self.template_name, {
            **_base_ctx(request, student),
            'form': form,
            'activity_type': activity_type,
            'is_edit': False,
            'title_prefix': f"Add {activity_type.replace('_', ' ').title()}"
        })

    def post(self, request, activity_type, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return redirect('accounts:logout')

        if activity_type not in FORM_MAP:
            messages.error(request, "Invalid activity type.")
            return redirect('student_portal:journey')

        form_class, model_class = FORM_MAP[activity_type]
        
        if activity_type == 'project_milestone':
            form = form_class(request.POST, request.FILES, student=student)
        else:
            form = form_class(request.POST, request.FILES)

        if form.is_valid():
            obj = form.save(commit=False)
            obj.student = student
            obj.save()
            messages.success(request, f"{activity_type.replace('_', ' ').title()} recorded successfully.")
            return redirect('student_portal:journey')

        return render(request, self.template_name, {
            **_base_ctx(request, student),
            'form': form,
            'activity_type': activity_type,
            'is_edit': False,
            'title_prefix': f"Add {activity_type.replace('_', ' ').title()}"
        })


class EditJourneyActivityView(StudentRequiredMixin, View):
    template_name = 'student_portal/journey_form.html'

    def get(self, request, activity_type, pk, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return redirect('accounts:logout')

        if activity_type not in FORM_MAP:
            messages.error(request, "Invalid activity type.")
            return redirect('student_portal:journey')

        form_class, model_class = FORM_MAP[activity_type]
        obj = get_object_or_404(model_class, pk=pk, student=student)
        
        if activity_type == 'project_milestone':
            form = form_class(instance=obj, student=student)
        else:
            form = form_class(instance=obj)

        return render(request, self.template_name, {
            **_base_ctx(request, student),
            'form': form,
            'activity_type': activity_type,
            'is_edit': True,
            'title_prefix': f"Edit {activity_type.replace('_', ' ').title()}"
        })

    def post(self, request, activity_type, pk, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return redirect('accounts:logout')

        if activity_type not in FORM_MAP:
            messages.error(request, "Invalid activity type.")
            return redirect('student_portal:journey')

        form_class, model_class = FORM_MAP[activity_type]
        obj = get_object_or_404(model_class, pk=pk, student=student)

        if activity_type == 'project_milestone':
            form = form_class(request.POST, request.FILES, instance=obj, student=student)
        else:
            form = form_class(request.POST, request.FILES, instance=obj)

        if form.is_valid():
            form.save()
            messages.success(request, f"{activity_type.replace('_', ' ').title()} updated successfully.")
            return redirect('student_portal:journey')

        return render(request, self.template_name, {
            **_base_ctx(request, student),
            'form': form,
            'activity_type': activity_type,
            'is_edit': True,
            'title_prefix': f"Edit {activity_type.replace('_', ' ').title()}"
        })


class DeleteJourneyActivityView(StudentRequiredMixin, View):
    template_name = 'student_portal/journey_confirm_delete.html'

    def get(self, request, activity_type, pk, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return redirect('accounts:logout')

        if activity_type not in FORM_MAP:
            messages.error(request, "Invalid activity type.")
            return redirect('student_portal:journey')

        form_class, model_class = FORM_MAP[activity_type]
        obj = get_object_or_404(model_class, pk=pk, student=student)
        return render(request, self.template_name, {
            **_base_ctx(request, student),
            'object': obj,
            'activity_type': activity_type,
        })

    def post(self, request, activity_type, pk, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return redirect('accounts:logout')

        if activity_type not in FORM_MAP:
            messages.error(request, "Invalid activity type.")
            return redirect('student_portal:journey')

        form_class, model_class = FORM_MAP[activity_type]
        obj = get_object_or_404(model_class, pk=pk, student=student)
        obj.delete()
        messages.success(request, f"{activity_type.replace('_', ' ').title()} has been deleted.")
        return redirect('student_portal:journey')


class TechnicalLinksUpdateView(StudentRequiredMixin, View):
    template_name = 'student_portal/journey_form.html'

    def get(self, request, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return redirect('accounts:logout')

        links, created = TechnicalLinks.objects.get_or_create(student=student)
        form = TechnicalLinksForm(instance=links)
        return render(request, self.template_name, {
            **_base_ctx(request, student),
            'form': form,
            'is_edit': True,
            'title_prefix': 'Update Technical Links'
        })

    def post(self, request, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return redirect('accounts:logout')

        links, created = TechnicalLinks.objects.get_or_create(student=student)
        form = TechnicalLinksForm(request.POST, instance=links)
        if form.is_valid():
            form.save()
            messages.success(request, "Technical links updated successfully.")
            return redirect('student_portal:journey')

        return render(request, self.template_name, {
            **_base_ctx(request, student),
            'form': form,
            'is_edit': True,
            'title_prefix': 'Update Technical Links'
        })


class RecruiterDeveloperJourneyView(LoginRequiredMixin, View):
    template_name = 'student_portal/journey_list.html'

    def get(self, request, student_id, *args, **kwargs):
        student = get_object_or_404(Student, pk=student_id)

        available_years = _get_available_years(student)
        selected_year = _resolve_selected_year(request, available_years)

        heatmap_cols = _get_heatmap_cols(student, selected_year)
        selected_year_activity_count = Activity.objects.filter(
            student=student, date__year=selected_year
        ).count()

        date_str = request.GET.get('date', '').strip()
        category_filter = request.GET.get('category', '').strip()

        activities = Activity.objects.filter(student=student)

        if date_str:
            try:
                clicked_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                activities = activities.filter(date=clicked_date)
            except ValueError:
                pass

        if category_filter:
            activities = activities.filter(category=category_filter)

        links, created = TechnicalLinks.objects.get_or_create(student=student)
        goals = LearningGoal.objects.filter(student=student)
        achievements = DeveloperAchievement.objects.filter(student=student)

        stats = _get_journey_stats(student)

        context = {
            'student': student,
            'heatmap_cols': heatmap_cols,
            'activities': activities,
            'links': links,
            'goals': goals,
            'achievements': achievements,
            'date_filter': date_str,
            'category_filter': category_filter,
            'available_years': available_years,
            'selected_year': selected_year,
            'selected_year_activity_count': selected_year_activity_count,
            'categories': Activity.Category.choices,
            'is_recruiter': True,
            **stats
        }
        return render(request, self.template_name, context)


# ─────────────────────────────────────────────────────────────────────────────
# Certificates Module Views
# ─────────────────────────────────────────────────────────────────────────────
from django.core.paginator import Paginator

class StudentCertificatesListView(LoginRequiredMixin, View):
    template_name = 'student_portal/certificates_list.html'

    def get(self, request, *args, **kwargs):
        student = request.user.student_profile
        
        # Get all student certificates
        qs = Certificate.objects.filter(student=student)

        # Calculate Summary Card Stats
        total_count = qs.count()
        courses_count = qs.filter(purpose='COURSE_COMPLETION').count()
        hackathons_count = qs.filter(purpose='HACKATHON').count()
        workshops_count = qs.filter(purpose='WORKSHOP').count()

        # Handle Search
        q = request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(title__icontains=q) |
                Q(issuing_organization__icontains=q) |
                Q(purpose__icontains=q)
            )

        # Handle Filters
        purpose = request.GET.get('purpose', '').strip()
        if purpose:
            qs = qs.filter(purpose=purpose)

        year = request.GET.get('year', '').strip()
        if year:
            try:
                qs = qs.filter(issue_date__year=int(year))
            except ValueError:
                pass

        sort = request.GET.get('sort', 'newest').strip()
        if sort == 'oldest':
            qs = qs.order_by('issue_date', 'created_at')
        else:
            qs = qs.order_by('-issue_date', '-created_at')

        # Pagination
        paginator = Paginator(qs, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        # Get list of unique years for the filter dropdown
        years = Certificate.objects.filter(student=student).values_list('issue_date__year', flat=True).distinct().order_by('-issue_date__year')

        context = {
            'student': student,
            'page_obj': page_obj,
            'total_count': total_count,
            'courses_count': courses_count,
            'hackathons_count': hackathons_count,
            'workshops_count': workshops_count,
            'q': q,
            'selected_purpose': purpose,
            'selected_year': year,
            'selected_sort': sort,
            'years': years,
            'purposes': Certificate.Purpose.choices,
            'is_recruiter': False,
        }
        return render(request, self.template_name, context)


class StudentCertificateCreateView(LoginRequiredMixin, View):
    form_class = CertificateForm
    template_name = 'student_portal/certificate_form.html'

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {
            'form': form,
            'title_prefix': 'Add Certificate',
            'is_edit': False
        })

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        if form.is_valid():
            certificate = form.save(commit=False)
            certificate.student = request.user.student_profile
            certificate.save()
            messages.success(request, "Certificate added successfully!")
            return redirect('student_portal:certificates_list')
        return render(request, self.template_name, {
            'form': form,
            'title_prefix': 'Add Certificate',
            'is_edit': False
        })


class StudentCertificateDetailView(LoginRequiredMixin, View):
    template_name = 'student_portal/certificate_detail.html'

    def get(self, request, pk, *args, **kwargs):
        student = request.user.student_profile
        certificate = get_object_or_404(Certificate, pk=pk, student=student)
        return render(request, self.template_name, {
            'certificate': certificate,
            'is_recruiter': False
        })


class StudentCertificateUpdateView(LoginRequiredMixin, View):
    form_class = CertificateForm
    template_name = 'student_portal/certificate_form.html'

    def get(self, request, pk, *args, **kwargs):
        student = request.user.student_profile
        certificate = get_object_or_404(Certificate, pk=pk, student=student)
        form = self.form_class(instance=certificate)
        return render(request, self.template_name, {
            'form': form,
            'title_prefix': 'Edit Certificate',
            'is_edit': True,
            'certificate': certificate
        })

    def post(self, request, pk, *args, **kwargs):
        student = request.user.student_profile
        certificate = get_object_or_404(Certificate, pk=pk, student=student)
        form = self.form_class(request.POST, request.FILES, instance=certificate)
        if form.is_valid():
            form.save()
            messages.success(request, "Certificate updated successfully!")
            return redirect('student_portal:certificate_detail', pk=pk)
        return render(request, self.template_name, {
            'form': form,
            'title_prefix': 'Edit Certificate',
            'is_edit': True,
            'certificate': certificate
        })


class StudentCertificateDeleteView(LoginRequiredMixin, View):
    template_name = 'student_portal/certificate_confirm_delete.html'

    def get(self, request, pk, *args, **kwargs):
        student = request.user.student_profile
        certificate = get_object_or_404(Certificate, pk=pk, student=student)
        return render(request, self.template_name, {'object': certificate})

    def post(self, request, pk, *args, **kwargs):
        student = request.user.student_profile
        certificate = get_object_or_404(Certificate, pk=pk, student=student)
        certificate.delete()
        messages.success(request, "Certificate removed successfully!")
        return redirect('student_portal:certificates_list')


# Recruiter Views (Read-Only)

class RecruiterCertificatesListView(LoginRequiredMixin, View):
    template_name = 'student_portal/certificates_list.html'

    def get(self, request, student_id, *args, **kwargs):
        student = get_object_or_404(Student, id=student_id)
        
        # Recruiter gets read-only list
        qs = Certificate.objects.filter(student=student)

        # Calculate Summary Card Stats
        total_count = qs.count()
        courses_count = qs.filter(purpose='COURSE_COMPLETION').count()
        hackathons_count = qs.filter(purpose='HACKATHON').count()
        workshops_count = qs.filter(purpose='WORKSHOP').count()

        # Search
        q = request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(title__icontains=q) |
                Q(issuing_organization__icontains=q) |
                Q(purpose__icontains=q)
            )

        # Filters
        purpose = request.GET.get('purpose', '').strip()
        if purpose:
            qs = qs.filter(purpose=purpose)

        year = request.GET.get('year', '').strip()
        if year:
            try:
                qs = qs.filter(issue_date__year=int(year))
            except ValueError:
                pass

        sort = request.GET.get('sort', 'newest').strip()
        if sort == 'oldest':
            qs = qs.order_by('issue_date', 'created_at')
        else:
            qs = qs.order_by('-issue_date', '-created_at')

        # Pagination
        paginator = Paginator(qs, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        years = Certificate.objects.filter(student=student).values_list('issue_date__year', flat=True).distinct().order_by('-issue_date__year')

        context = {
            'student': student,
            'page_obj': page_obj,
            'total_count': total_count,
            'courses_count': courses_count,
            'hackathons_count': hackathons_count,
            'workshops_count': workshops_count,
            'q': q,
            'selected_purpose': purpose,
            'selected_year': year,
            'selected_sort': sort,
            'years': years,
            'purposes': Certificate.Purpose.choices,
            'is_recruiter': True,
        }
        return render(request, self.template_name, context)


class RecruiterCertificateDetailView(LoginRequiredMixin, View):
    template_name = 'student_portal/certificate_detail.html'

    def get(self, request, pk, *args, **kwargs):
        certificate = get_object_or_404(Certificate, pk=pk)
        return render(request, self.template_name, {
            'certificate': certificate,
            'is_recruiter': True,
            'student': certificate.student
        })




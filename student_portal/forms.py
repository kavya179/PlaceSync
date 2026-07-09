from django import forms
from students.models import (
    StudentSkill, Project, TechnicalLinks, Activity, WeeklySummary, MonthlySummary,
    ProjectMilestone, HackathonJournal, CodingPractice, LearningJournal, OpenSourceContribution,
    LearningGoal, DeveloperAchievement
)


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        exclude = ['student', 'created_at', 'updated_at']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'sp-form-input', 'placeholder': 'e.g. Portfolio Builder'}),
            'short_description': forms.TextInput(attrs={'class': 'sp-form-input', 'placeholder': 'Brief 1-sentence tagline'}),
            'detailed_description': forms.Textarea(attrs={'class': 'sp-form-input', 'rows': 4, 'placeholder': 'Detailed explanation of project architecture, functionality...'}),
            'category': forms.Select(attrs={'class': 'sp-form-input'}),
            'project_type': forms.Select(attrs={'class': 'sp-form-input'}),
            'status': forms.Select(attrs={'class': 'sp-form-input'}),
            'technologies': forms.TextInput(attrs={'class': 'sp-form-input', 'placeholder': 'e.g. Python, Django, PostgreSQL (comma-separated)'}),
            'github_url': forms.URLInput(attrs={'class': 'sp-form-input', 'placeholder': 'https://github.com/...'}),
            'live_url': forms.URLInput(attrs={'class': 'sp-form-input', 'placeholder': 'https://...'}),
            'youtube_url': forms.URLInput(attrs={'class': 'sp-form-input', 'placeholder': 'YouTube Demo Video URL'}),
            'documentation_url': forms.URLInput(attrs={'class': 'sp-form-input', 'placeholder': 'Documentation website URL'}),
            'google_drive_url': forms.URLInput(attrs={'class': 'sp-form-input', 'placeholder': 'Google Drive folder/report URL'}),
            'figma_url': forms.URLInput(attrs={'class': 'sp-form-input', 'placeholder': 'Figma Design URL'}),
            'play_store_url': forms.URLInput(attrs={'class': 'sp-form-input', 'placeholder': 'Google Play Store URL'}),
            'app_store_url': forms.URLInput(attrs={'class': 'sp-form-input', 'placeholder': 'Apple App Store URL'}),
            'portfolio_url': forms.URLInput(attrs={'class': 'sp-form-input', 'placeholder': 'Personal Portfolio URL'}),
            'key_features': forms.Textarea(attrs={'class': 'sp-form-input', 'rows': 3, 'placeholder': 'e.g. User Authentication, REST API, Payment Gateway (comma-separated)'}),
            'achievements': forms.TextInput(attrs={'class': 'sp-form-input', 'placeholder': 'e.g. Hackathon Winner, Published (comma-separated)'}),
            'is_featured': forms.CheckboxInput(attrs={'style': 'margin-right: 0.5rem; transform: scale(1.15);'}),
        }


class StudentSkillForm(forms.ModelForm):
    """Form for adding / editing a StudentSkill entry."""

    class Meta:
        model  = StudentSkill
        fields = ['name', 'category', 'proficiency', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class':       'sp-form-input',
                'placeholder': 'e.g. Python, MySQL, Docker…',
                'autofocus':   True,
            }),
            'category': forms.Select(attrs={
                'class': 'sp-form-input',
            }),
            'proficiency': forms.Select(attrs={
                'class': 'sp-form-input',
            }),
            'description': forms.TextInput(attrs={
                'class':       'sp-form-input',
                'placeholder': 'Optional note e.g. 2 years experience, used in projects…',
            }),
        }
        labels = {
            'name':        'Skill Name',
            'category':    'Category',
            'proficiency': 'Proficiency Level',
            'description': 'Short Note (optional)',
        }


class ResumeUploadForm(forms.Form):
    """Form to upload/replace a PDF Resume or CV."""
    resume_type = forms.ChoiceField(
        choices=[('RESUME', 'Resume'), ('CV', 'CV')],
        widget=forms.Select(attrs={'class': 'sp-form-input'}),
        label='File Type'
    )
    file = forms.FileField(
        widget=forms.FileInput(attrs={'class': 'sp-form-input', 'accept': '.pdf'}),
        label='Choose PDF File'
    )

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # 1. Extension check
            if not file.name.lower().endswith('.pdf'):
                raise forms.ValidationError("Only PDF documents are allowed.")
            # 2. File size check (5 MB)
            if file.size > 5 * 1024 * 1024:
                raise forms.ValidationError("File size must be under 5 MB.")
        return file


# ─────────────────────────────────────────────────────────────────────────────
# TechnicalLinksForm
# ─────────────────────────────────────────────────────────────────────────────

class TechnicalLinksForm(forms.ModelForm):
    class Meta:
        model = TechnicalLinks
        exclude = ['student']
        widgets = {
            'github': forms.URLInput(attrs={'class': 'sp-form-input', 'placeholder': 'https://github.com/username'}),
            'leetcode': forms.URLInput(attrs={'class': 'sp-form-input', 'placeholder': 'https://leetcode.com/username'}),
            'codechef': forms.URLInput(attrs={'class': 'sp-form-input', 'placeholder': 'https://www.codechef.com/users/username'}),
            'codeforces': forms.URLInput(attrs={'class': 'sp-form-input', 'placeholder': 'https://codeforces.com/profile/username'}),
            'hackerrank': forms.URLInput(attrs={'class': 'sp-form-input', 'placeholder': 'https://www.hackerrank.com/username'}),
            'geeksforgeeks': forms.URLInput(attrs={'class': 'sp-form-input', 'placeholder': 'https://auth.geeksforgeeks.org/user/username'}),
            'kaggle': forms.URLInput(attrs={'class': 'sp-form-input', 'placeholder': 'https://www.kaggle.com/username'}),
            'portfolio': forms.URLInput(attrs={'class': 'sp-form-input', 'placeholder': 'https://yourportfolio.com'}),
            'linkedin': forms.URLInput(attrs={'class': 'sp-form-input', 'placeholder': 'https://linkedin.com/in/username'}),
        }


# ─────────────────────────────────────────────────────────────────────────────
# ActivityForm (Daily Log & Generic Updates)
# ─────────────────────────────────────────────────────────────────────────────

class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ['title', 'description', 'category', 'date', 'hours_spent', 'technology_tags', 'status', 'attachment']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'sp-form-input', 'placeholder': 'e.g. Solved 5 LeetCode Problems'}),
            'description': forms.Textarea(attrs={'class': 'sp-form-input', 'rows': 4, 'placeholder': 'e.g. Practiced Binary Trees DFS and dynamic programming...'}),
            'category': forms.Select(attrs={'class': 'sp-form-input'}),
            'date': forms.DateInput(attrs={'class': 'sp-form-input', 'type': 'date'}),
            'hours_spent': forms.NumberInput(attrs={'class': 'sp-form-input', 'min': 0, 'step': '0.1'}),
            'technology_tags': forms.TextInput(attrs={'class': 'sp-form-input', 'placeholder': 'e.g. Python, Algorithms (comma-separated)'}),
            'status': forms.Select(attrs={'class': 'sp-form-input'}),
            'attachment': forms.FileInput(attrs={'class': 'sp-form-input'}),
        }


# ─────────────────────────────────────────────────────────────────────────────
# WeeklySummaryForm
# ─────────────────────────────────────────────────────────────────────────────

class WeeklySummaryForm(forms.ModelForm):
    class Meta:
        model = WeeklySummary
        exclude = ['student']
        widgets = {
            'week_number': forms.NumberInput(attrs={'class': 'sp-form-input', 'min': 1, 'placeholder': 'e.g. 1, 2'}),
            'summary': forms.Textarea(attrs={'class': 'sp-form-input', 'rows': 4, 'placeholder': 'Detail your coding progress and milestones...'}),
            'hours': forms.NumberInput(attrs={'class': 'sp-form-input', 'min': 0, 'step': '0.1'}),
            'problems_solved': forms.NumberInput(attrs={'class': 'sp-form-input', 'min': 0}),
            'projects_worked': forms.TextInput(attrs={'class': 'sp-form-input', 'placeholder': 'e.g. PlaceSync Dashboard, Compiler Design'}),
            'skills_learned': forms.TextInput(attrs={'class': 'sp-form-input', 'placeholder': 'e.g. Django ORM, REST API (comma-separated)'}),
            'challenges': forms.Textarea(attrs={'class': 'sp-form-input', 'rows': 3, 'placeholder': 'e.g. Debugging database deadlocks...'}),
            'date': forms.DateInput(attrs={'class': 'sp-form-input', 'type': 'date'}),
        }


# ─────────────────────────────────────────────────────────────────────────────
# MonthlySummaryForm
# ─────────────────────────────────────────────────────────────────────────────

class MonthlySummaryForm(forms.ModelForm):
    class Meta:
        model = MonthlySummary
        exclude = ['student']
        widgets = {
            'month': forms.TextInput(attrs={'class': 'sp-form-input', 'placeholder': 'e.g. January 2026'}),
            'achievements': forms.Textarea(attrs={'class': 'sp-form-input', 'rows': 3, 'placeholder': 'Key milestones reached...'}),
            'projects_completed': forms.TextInput(attrs={'class': 'sp-form-input', 'placeholder': 'e.g. Recommendation Engine'}),
            'technologies_learned': forms.TextInput(attrs={'class': 'sp-form-input', 'placeholder': 'e.g. PyTorch, Docker (comma-separated)'}),
            'certificates': forms.TextInput(attrs={'class': 'sp-form-input', 'placeholder': 'e.g. AWS Cloud Practitioner'}),
            'goals': forms.Textarea(attrs={'class': 'sp-form-input', 'rows': 3, 'placeholder': 'Goals achieved or set...'}),
            'date': forms.DateInput(attrs={'class': 'sp-form-input', 'type': 'date'}),
        }


# ─────────────────────────────────────────────────────────────────────────────
# ProjectMilestoneForm
# ─────────────────────────────────────────────────────────────────────────────

class ProjectMilestoneForm(forms.ModelForm):
    class Meta:
        model = ProjectMilestone
        exclude = ['student']
        widgets = {
            'project': forms.Select(attrs={'class': 'sp-form-input'}),
            'milestone': forms.TextInput(attrs={'class': 'sp-form-input', 'placeholder': 'e.g. Build Login Module'}),
            'progress_pct': forms.NumberInput(attrs={'class': 'sp-form-input', 'min': 0, 'max': 100, 'placeholder': 'e.g. 50'}),
            'hours': forms.NumberInput(attrs={'class': 'sp-form-input', 'min': 0, 'step': '0.1'}),
            'technologies': forms.TextInput(attrs={'class': 'sp-form-input', 'placeholder': 'e.g. HTML, CSS, Django (comma-separated)'}),
            'status': forms.Select(attrs={'class': 'sp-form-input'}),
            'date': forms.DateInput(attrs={'class': 'sp-form-input', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        student = kwargs.pop('student', None)
        super().__init__(*args, **kwargs)
        if student:
            # Only list student's own projects
            self.fields['project'].queryset = Project.objects.filter(student=student)


# ─────────────────────────────────────────────────────────────────────────────
# HackathonJournalForm
# ─────────────────────────────────────────────────────────────────────────────

class HackathonJournalForm(forms.ModelForm):
    class Meta:
        model = HackathonJournal
        exclude = ['student']
        widgets = {
            'hackathon_name': forms.TextInput(attrs={'class': 'sp-form-input', 'placeholder': 'e.g. Smart India Hackathon'}),
            'organizer': forms.TextInput(attrs={'class': 'sp-form-input', 'placeholder': 'e.g. Ministry of Education'}),
            'date': forms.DateInput(attrs={'class': 'sp-form-input', 'type': 'date'}),
            'theme': forms.TextInput(attrs={'class': 'sp-form-input', 'placeholder': 'e.g. Fintech Solutions'}),
            'team': forms.Textarea(attrs={'class': 'sp-form-input', 'rows': 2, 'placeholder': 'e.g. Team Lead: John, Backend: Bob...'}),
            'role': forms.TextInput(attrs={'class': 'sp-form-input', 'placeholder': 'e.g. Lead Backend Engineer'}),
            'project': forms.TextInput(attrs={'class': 'sp-form-input', 'placeholder': 'e.g. PlaceSync App'}),
            'technologies': forms.TextInput(attrs={'class': 'sp-form-input', 'placeholder': 'e.g. Python, PostgreSQL (comma-separated)'}),
            'challenges': forms.Textarea(attrs={'class': 'sp-form-input', 'rows': 3, 'placeholder': 'Describe technical difficulties and debugging...'}),
            'learning': forms.Textarea(attrs={'class': 'sp-form-input', 'rows': 3, 'placeholder': 'What did you learn?'}),
            'achievement': forms.TextInput(attrs={'class': 'sp-form-input', 'placeholder': 'e.g. 1st Place Winner, Runner Up'}),
            'certificate': forms.FileInput(attrs={'class': 'sp-form-input'}),
            'repository': forms.URLInput(attrs={'class': 'sp-form-input', 'placeholder': 'GitHub repository link'}),
            'presentation': forms.URLInput(attrs={'class': 'sp-form-input', 'placeholder': 'Figma, SlideShare or drive link'}),
            'photo': forms.FileInput(attrs={'class': 'sp-form-input'}),
        }


# ─────────────────────────────────────────────────────────────────────────────
# CodingPracticeForm
# ─────────────────────────────────────────────────────────────────────────────

class CodingPracticeForm(forms.ModelForm):
    class Meta:
        model = CodingPractice
        exclude = ['student']
        widgets = {
            'platform': forms.Select(attrs={'class': 'sp-form-input'}),
            'problems_solved': forms.NumberInput(attrs={'class': 'sp-form-input', 'min': 1}),
            'difficulty': forms.TextInput(attrs={'class': 'sp-form-input', 'placeholder': 'e.g. 3 Easy, 2 Medium'}),
            'topics': forms.TextInput(attrs={'class': 'sp-form-input', 'placeholder': 'e.g. DFS, BFS, Dynamic Programming'}),
            'notes': forms.Textarea(attrs={'class': 'sp-form-input', 'rows': 3, 'placeholder': 'e.g. Solved with O(N) complexity using hash map...'}),
            'date': forms.DateInput(attrs={'class': 'sp-form-input', 'type': 'date'}),
        }


# ─────────────────────────────────────────────────────────────────────────────
# LearningJournalForm
# ─────────────────────────────────────────────────────────────────────────────

class LearningJournalForm(forms.ModelForm):
    class Meta:
        model = LearningJournal
        exclude = ['student']
        widgets = {
            'course': forms.TextInput(attrs={'class': 'sp-form-input', 'placeholder': 'e.g. Machine Learning Specialization'}),
            'platform': forms.TextInput(attrs={'class': 'sp-form-input', 'placeholder': 'e.g. Coursera, Udemy'}),
            'duration': forms.TextInput(attrs={'class': 'sp-form-input', 'placeholder': 'e.g. 12 hours, 3 weeks'}),
            'progress': forms.NumberInput(attrs={'class': 'sp-form-input', 'min': 0, 'max': 100, 'placeholder': 'Progress %'}),
            'topics': forms.TextInput(attrs={'class': 'sp-form-input', 'placeholder': 'e.g. Linear Regression, Neural Networks'}),
            'certificate': forms.FileInput(attrs={'class': 'sp-form-input'}),
            'notes': forms.Textarea(attrs={'class': 'sp-form-input', 'rows': 4, 'placeholder': 'Optimal solutions and structures learned...'}),
            'date': forms.DateInput(attrs={'class': 'sp-form-input', 'type': 'date'}),
        }


# ─────────────────────────────────────────────────────────────────────────────
# OpenSourceContributionForm
# ─────────────────────────────────────────────────────────────────────────────

class OpenSourceContributionForm(forms.ModelForm):
    class Meta:
        model = OpenSourceContribution
        exclude = ['student']
        widgets = {
            'repository': forms.TextInput(attrs={'class': 'sp-form-input', 'placeholder': 'e.g. django/django'}),
            'contribution': forms.Textarea(attrs={'class': 'sp-form-input', 'rows': 3, 'placeholder': 'Describe code contributed...'}),
            'pull_request': forms.URLInput(attrs={'class': 'sp-form-input', 'placeholder': 'https://github.com/django/django/pull/...'}),
            'issue': forms.URLInput(attrs={'class': 'sp-form-input', 'placeholder': 'https://github.com/django/django/issues/...'}),
            'date': forms.DateInput(attrs={'class': 'sp-form-input', 'type': 'date'}),
            'learning': forms.Textarea(attrs={'class': 'sp-form-input', 'rows': 2, 'placeholder': 'Learned codebase styling/standards...'}),
        }


# ─────────────────────────────────────────────────────────────────────────────
# LearningGoalForm
# ─────────────────────────────────────────────────────────────────────────────

class LearningGoalForm(forms.ModelForm):
    class Meta:
        model = LearningGoal
        exclude = ['student']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'sp-form-input', 'placeholder': 'e.g. Learn System Design basics'}),
            'priority': forms.Select(attrs={'class': 'sp-form-input'}),
            'target_date': forms.DateInput(attrs={'class': 'sp-form-input', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'sp-form-input'}),
        }


# ─────────────────────────────────────────────────────────────────────────────
# DeveloperAchievementForm
# ─────────────────────────────────────────────────────────────────────────────

class DeveloperAchievementForm(forms.ModelForm):
    class Meta:
        model = DeveloperAchievement
        exclude = ['student']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'sp-form-input', 'placeholder': 'e.g. Research Publication in IEEE'}),
            'category': forms.Select(attrs={'class': 'sp-form-input'}),
            'date': forms.DateInput(attrs={'class': 'sp-form-input', 'type': 'date'}),
            'description': forms.Textarea(attrs={'class': 'sp-form-input', 'rows': 4, 'placeholder': 'Provide context, link, or verification details...'}),
            'certificate': forms.FileInput(attrs={'class': 'sp-form-input'}),
        }



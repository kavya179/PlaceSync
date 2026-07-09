from django.urls import path
from .views import (
    StudentDashboardView,
    StudentProfileView,
    StudentProfileEditView,
    StudentDrivesView,
    StudentDriveDetailView,
    StudentBookmarkToggleView,
    StudentApplyView,
    StudentApplicationsView,
    StudentNotificationsView,
    StudentMarkNotificationReadView,
    StudentSettingsView,
    StudentResumeUploadView,
    # Resume Version History & ATS Analysis
    StudentResumeDashboardView,
    StudentResumeDownloadView,
    StudentResumeDeleteView,
    StudentResumeCompareView,
    # Skills
    StudentSkillsView,
    StudentSkillAddView,
    StudentSkillEditView,
    StudentSkillDeleteView,
    # Calendar
    StudentCalendarView,
    # Recommendations
    StudentRecommendationsView,
    # Analytics & PDF
    StudentAnalyticsView,
    StudentCareerPassportPdfView,
    # Projects
    StudentProjectsListView,
    StudentProjectCreateView,
    StudentProjectUpdateView,
    StudentProjectDeleteView,
    StudentProjectDetailView,
    RecruiterPortfolioView,
    RecruiterProjectDetailView,
    # Developer Journey
    DeveloperJourneyListView,
    AddJourneyActivityView,
    EditJourneyActivityView,
    DeleteJourneyActivityView,
    TechnicalLinksUpdateView,
    RecruiterDeveloperJourneyView,
)

app_name = 'student_portal'

urlpatterns = [
    path('',                                  StudentDashboardView.as_view(),             name='dashboard'),
    path('profile/',                          StudentProfileView.as_view(),               name='profile'),
    path('profile/edit/',                     StudentProfileEditView.as_view(),           name='profile_edit'),
    
    # Resume Management & ATS Analysis
    path('resume/',                           StudentResumeDashboardView.as_view(),       name='resume_dashboard'),
    path('resume/upload/',                    StudentResumeUploadView.as_view(),          name='resume_upload'),
    path('resume/download/<int:pk>/',         StudentResumeDownloadView.as_view(),        name='resume_download'),
    path('resume/delete/<int:pk>/',           StudentResumeDeleteView.as_view(),          name='resume_delete'),
    path('resume/compare/',                   StudentResumeCompareView.as_view(),         name='resume_compare'),

    # Skills
    path('skills/',                           StudentSkillsView.as_view(),                name='skills'),
    path('skills/add/',                       StudentSkillAddView.as_view(),              name='skill_add'),
    path('skills/<int:pk>/edit/',             StudentSkillEditView.as_view(),             name='skill_edit'),
    path('skills/<int:pk>/delete/',           StudentSkillDeleteView.as_view(),           name='skill_delete'),

    # Placement drives & applications
    path('drives/',                           StudentDrivesView.as_view(),                name='drives'),
    path('drives/<int:pk>/',                  StudentDriveDetailView.as_view(),           name='drive_detail'),
    path('drives/<int:pk>/bookmark/',         StudentBookmarkToggleView.as_view(),        name='bookmark_toggle'),
    path('drives/<int:pk>/apply/',            StudentApplyView.as_view(),                 name='apply'),
    path('applications/',                     StudentApplicationsView.as_view(),          name='applications'),

    # Calendar
    path('calendar/',                         StudentCalendarView.as_view(),              name='calendar'),

    # Recommendations
    path('recommendations/',                  StudentRecommendationsView.as_view(),       name='recommendations'),

    # Analytics
    path('analytics/',                        StudentAnalyticsView.as_view(),             name='analytics'),
    path('analytics/passport/pdf/',           StudentCareerPassportPdfView.as_view(),     name='passport_pdf'),

    # Notifications
    path('notifications/',                    StudentNotificationsView.as_view(),         name='notifications'),
    path('notifications/<int:pk>/read/',      StudentMarkNotificationReadView.as_view(),  name='notification_read'),

    # Settings
    path('settings/',                         StudentSettingsView.as_view(),              name='settings'),

    # Projects & Developer Portfolio
    path('projects/',                         StudentProjectsListView.as_view(),          name='projects_list'),
    path('projects/add/',                     StudentProjectCreateView.as_view(),         name='project_create'),
    path('projects/<int:pk>/',                StudentProjectDetailView.as_view(),         name='project_detail'),
    path('projects/<int:pk>/edit/',           StudentProjectUpdateView.as_view(),         name='project_edit'),
    path('projects/<int:pk>/delete/',         StudentProjectDeleteView.as_view(),         name='project_delete'),
    path('portfolio/<int:student_id>/',       RecruiterPortfolioView.as_view(),           name='recruiter_portfolio'),
    path('portfolio/project/<int:pk>/',       RecruiterProjectDetailView.as_view(),       name='recruiter_project_detail'),

    # Developer Journey
    path('journey/',                          DeveloperJourneyListView.as_view(),         name='journey'),
    path('journey/links/',                    TechnicalLinksUpdateView.as_view(),         name='journey_links'),
    path('journey/add/<str:activity_type>/',  AddJourneyActivityView.as_view(),          name='journey_add'),
    path('journey/edit/<str:activity_type>/<int:pk>/', EditJourneyActivityView.as_view(), name='journey_edit'),
    path('journey/delete/<str:activity_type>/<int:pk>/', DeleteJourneyActivityView.as_view(), name='journey_delete'),
    path('portfolio/journey/<int:student_id>/', RecruiterDeveloperJourneyView.as_view(),  name='recruiter_journey'),
]

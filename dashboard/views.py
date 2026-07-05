from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.db.models import Avg, Max, Count, Q
from django.utils import timezone


class DashboardIndexView(LoginRequiredMixin, View):
    template_name = 'dashboard/index.html'

    def get(self, request, *args, **kwargs):
        college = getattr(request.user, 'college', None)
        stats = {}
        recent_drives = []
        recent_applications = []

        try:
            from students.models import StudentProfile
            qs = StudentProfile.objects.filter(batch__college=college) if college else StudentProfile.objects.none()
            stats['total_students'] = qs.count()
            stats['placed_students'] = qs.filter(placement_status='placed').count()
            total = stats['total_students'] or 1
            stats['placement_ratio'] = round(stats['placed_students'] / total * 100, 1)
            stats['avg_cgpa'] = round(qs.aggregate(a=Avg('cgpa'))['a'] or 0, 2)
        except Exception:
            stats.setdefault('total_students', 0)
            stats.setdefault('placed_students', 0)
            stats.setdefault('placement_ratio', 0)
            stats.setdefault('avg_cgpa', 0)

        try:
            from companies.models import Company
            stats['total_companies'] = Company.objects.filter(college=college).count() if college else 0
            stats['verified_companies'] = Company.objects.filter(
                college=college, verification_status='verified'
            ).count() if college else 0
        except Exception:
            stats.setdefault('total_companies', 0)
            stats.setdefault('verified_companies', 0)

        try:
            from placements.models import PlacementDrive, Application
            drives_qs = PlacementDrive.objects.filter(college=college) if college else PlacementDrive.objects.none()
            stats['active_drives'] = drives_qs.filter(status='active').count()
            stats['total_drives'] = drives_qs.count()
            stats['total_applications'] = Application.objects.filter(drive__college=college).count() if college else 0
            recent_drives = list(drives_qs.order_by('-created_at')[:5])
        except Exception:
            stats.setdefault('active_drives', 0)
            stats.setdefault('total_drives', 0)
            stats.setdefault('total_applications', 0)

        try:
            from opportunities.models import Opportunity
            stats['active_opportunities'] = Opportunity.objects.filter(
                college=college, status='active'
            ).count() if college else 0
        except Exception:
            stats.setdefault('active_opportunities', 0)

        try:
            from communication.models import Notification
            stats['unread_notifications'] = Notification.objects.filter(
                college=college, is_read=False
            ).count() if college else 0
        except Exception:
            stats.setdefault('unread_notifications', 0)

        context = {
            'stats': stats,
            'recent_drives': recent_drives,
            'recent_applications': recent_applications,
        }
        return render(request, self.template_name, context)

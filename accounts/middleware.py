from django.shortcuts import redirect
from django.urls import reverse

class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Only enforce on students who have must_change_password=True
            if request.user.role == 'STUDENT' and getattr(request.user, 'must_change_password', False):
                # Allowed paths
                allowed_paths = [
                    reverse('accounts:password_change'),
                    reverse('accounts:logout'),
                ]
                
                # Check if current path is in allowed paths or is a static/media asset
                if request.path not in allowed_paths and not request.path.startswith('/static/') and not request.path.startswith('/media/'):
                    return redirect('accounts:password_change')
                    
        return self.get_response(request)

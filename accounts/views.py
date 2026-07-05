from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.contrib import messages
from django.urls import reverse_lazy
from .forms import CollegeRegistrationForm, CollegeLoginForm

class CollegeRegistrationView(View):
    form_class = CollegeRegistrationForm
    template_name = 'accounts/register.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard:index')
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard:index')
        form = self.form_class(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome to PlaceSync, {user.college.name} Admin!")
            return redirect('dashboard:index')
        return render(request, self.template_name, {'form': form})


class CollegeLoginView(LoginView):
    authentication_form = CollegeLoginForm
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True


class CollegeLogoutView(View):
    def get(self, request, *args, **kwargs):
        logout(request)
        messages.info(request, "You have been logged out successfully.")
        return redirect('accounts:login')

    def post(self, request, *args, **kwargs):
        logout(request)
        messages.info(request, "You have been logged out successfully.")
        return redirect('accounts:login')


class StudentPasswordChangeView(PasswordChangeView):
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('dashboard:index')

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.request.user
        user.must_change_password = False
        user.save()
        messages.success(self.request, "Your password has been changed successfully. You now have full dashboard access.")
        return response


from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render

from .forms import EmailAuthenticationForm, UserRegisterForm


class UserLoginView(LoginView):
    authentication_form = EmailAuthenticationForm
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        if user.is_admin_role:
            return '/admin/'
        if user.is_teacher_role:
            return '/teacher/'
        return '/dashboard/'


def register_page(request):
    if request.user.is_authenticated:
        if request.user.is_admin_role:
            return redirect('admin:index')
        if request.user.is_teacher_role:
            return redirect('teacher-dashboard')
        return redirect('dashboard')
    form = UserRegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect('dashboard')
    return render(request, 'accounts/register.html', {'form': form})

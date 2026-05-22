from django.urls import path

from .views import LoginView, ProfileView, RegisterView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('login/', LoginView.as_view(), name='auth-login'),
    path('profile/', ProfileView.as_view(), name='auth-profile'),
]

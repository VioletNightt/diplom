from django.contrib.auth.views import LogoutView
from django.urls import path

from accounts.frontend_views import UserLoginView, register_page
from events.frontend_views import (
    cancel_registration_page,
    dashboard_page,
    event_type_page,
    home_page,
    register_slot_page,
    teacher_attendance_page,
    teacher_dashboard_page,
    teacher_slot_cancel_page,
    teacher_slot_create_page,
    teacher_slot_edit_page,
)

urlpatterns = [
    path('', home_page, name='home'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='home'), name='logout'),
    path('register/', register_page, name='register-page'),
    path('dashboard/', dashboard_page, name='dashboard'),
    path('events/<str:event_type>/', event_type_page, name='event-type'),
    path('slots/<int:slot_id>/register/', register_slot_page, name='register-slot'),
    path('registrations/<int:registration_id>/cancel/', cancel_registration_page, name='cancel-registration'),
    path('teacher/', teacher_dashboard_page, name='teacher-dashboard'),
    path('teacher/slots/new/', teacher_slot_create_page, name='teacher-slot-create'),
    path('teacher/slots/<int:slot_id>/edit/', teacher_slot_edit_page, name='teacher-slot-edit'),
    path('teacher/slots/<int:slot_id>/cancel/', teacher_slot_cancel_page, name='teacher-slot-cancel'),
    path(
        'teacher/registrations/<int:registration_id>/attendance/<str:value>/',
        teacher_attendance_page,
        name='teacher-attendance',
    ),
]

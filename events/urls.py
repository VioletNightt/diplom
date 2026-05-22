from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    EventViewSet,
    ClassroomViewSet,
    MyRegistrationsViewSet,
    RegistrationViewSet,
    RegistrationsBySlotView,
    SchoolClassViewSet,
    SlotViewSet,
    TeacherProfileViewSet,
    TeacherSlotsView,
)

router = DefaultRouter()
router.register('events', EventViewSet, basename='event')
router.register('classrooms', ClassroomViewSet, basename='classroom')
router.register('school-classes', SchoolClassViewSet, basename='school-class')
router.register('slots', SlotViewSet, basename='slot')
router.register('registrations', RegistrationViewSet, basename='registration')
router.register('my-registrations', MyRegistrationsViewSet, basename='my-registration')
router.register('teachers', TeacherProfileViewSet, basename='teacher')

urlpatterns = [
    path('teacher-slots/<int:teacher_id>/', TeacherSlotsView.as_view(), name='teacher-slots'),
    path('registrations/by-slot/<int:slot_id>/', RegistrationsBySlotView.as_view(), name='registrations-by-slot'),
    path('', include(router.urls)),
]

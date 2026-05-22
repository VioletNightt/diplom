from django.http import HttpResponse
from rest_framework import decorators, exceptions, generics, permissions, response, status, viewsets

from .models import Classroom, Event, Registration, SchoolClass, Slot, TeacherProfile
from .permissions import IsAdminOrReadOnly
from .serializers import (
    AttendanceSerializer,
    ClassroomSerializer,
    EventSerializer,
    RegistrationCreateSerializer,
    RegistrationSerializer,
    SchoolClassSerializer,
    SlotSerializer,
    TeacherProfileSerializer,
)
from .services import RegistrationError, cancel_registration, create_registration, mark_attendance


class EventViewSet(viewsets.ModelViewSet):
    serializer_class = EventSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = Event.objects.select_related('created_by')
        event_type = self.request.query_params.get('type') or self.request.query_params.get('event_type')
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        if not self.request.user.is_admin_role:
            queryset = queryset.filter(is_active=True)
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ClassroomViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ClassroomSerializer

    def get_queryset(self):
        queryset = Classroom.objects.order_by('floor', 'number')
        if not self.request.user.is_admin_role:
            queryset = queryset.filter(is_active=True)
        return queryset


class SchoolClassViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SchoolClassSerializer

    def get_queryset(self):
        queryset = SchoolClass.objects.order_by('name')
        if not self.request.user.is_admin_role:
            queryset = queryset.filter(is_active=True)
        return queryset


class SlotViewSet(viewsets.ModelViewSet):
    serializer_class = SlotSerializer

    def get_permissions(self):
        if self.action in {'create', 'update', 'partial_update', 'destroy'}:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        queryset = Slot.objects.select_related('event', 'teacher', 'teacher__user', 'classroom').prefetch_related('available_classes')
        event_id = self.request.query_params.get('event_id')
        teacher_id = self.request.query_params.get('teacher')
        event_type = self.request.query_params.get('event_type')
        subject = self.request.query_params.get('subject')
        target_class = self.request.query_params.get('target_class')
        available = self.request.query_params.get('available')
        if event_id:
            queryset = queryset.filter(event_id=event_id)
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)
        if event_type:
            queryset = queryset.filter(event__event_type=event_type)
        if subject:
            queryset = queryset.filter(subject=subject)
        if target_class:
            queryset = queryset.filter(target_class=target_class)
        if available in {'1', 'true', 'True'}:
            queryset = queryset.filter(status=Slot.Status.OPEN, event__is_active=True)
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        if user.is_admin_role:
            serializer.save()
            return
        if user.is_teacher_role:
            teacher_profile = user.teacher_profile
            event = serializer.validated_data['event']
            if event.event_type != Event.EventType.MEETING:
                raise exceptions.PermissionDenied('Учитель может создавать только слоты встреч.')
            serializer.save(teacher=teacher_profile)
            return
        raise exceptions.PermissionDenied('Недостаточно прав.')

    def perform_update(self, serializer):
        user = self.request.user
        slot = self.get_object()
        if user.is_admin_role:
            serializer.save()
            return
        if user.is_teacher_role and slot.teacher.user_id == user.id:
            serializer.save(teacher=slot.teacher)
            return
        raise exceptions.PermissionDenied('Недостаточно прав.')


class RegistrationViewSet(viewsets.ModelViewSet):
    serializer_class = RegistrationSerializer

    def get_queryset(self):
        queryset = Registration.objects.select_related('slot', 'slot__event', 'slot__teacher', 'slot__teacher__user', 'user')
        user = self.request.user
        if user.is_admin_role:
            return queryset
        if user.is_teacher_role:
            teacher_profile = getattr(user, 'teacher_profile', None)
            return queryset.filter(slot__teacher=teacher_profile)
        return queryset.filter(user=user)

    def create(self, request, *args, **kwargs):
        serializer = RegistrationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            registration = create_registration(
                user=request.user,
                slot_id=serializer.validated_data['slot'],
                registration_data=serializer.validated_data.get('registration_data', {}),
            )
        except RegistrationError as exc:
            return response.Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return response.Response(RegistrationSerializer(registration, context={'request': request}).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        registration = self.get_object()
        if not request.user.is_admin_role and registration.user_id != request.user.id:
            return response.Response({'detail': 'Недостаточно прав.'}, status=status.HTTP_403_FORBIDDEN)
        cancel_registration(registration)
        return response.Response(status=status.HTTP_204_NO_CONTENT)

    @decorators.action(detail=True, methods=['post', 'patch'], permission_classes=[permissions.IsAuthenticated])
    def attendance(self, request, pk=None):
        registration = self.get_object()
        teacher_user_id = registration.slot.teacher.user_id if registration.slot.teacher_id else None
        if not (request.user.is_admin_role or (request.user.is_teacher_role and teacher_user_id == request.user.id)):
            return response.Response({'detail': 'Недостаточно прав.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = AttendanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        registration = mark_attendance(registration, serializer.validated_data['attended'])
        return response.Response(RegistrationSerializer(registration).data)


class MyRegistrationsViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RegistrationSerializer

    def get_queryset(self):
        return Registration.objects.select_related('slot', 'slot__event', 'slot__teacher', 'slot__teacher__user').filter(user=self.request.user)


class TeacherProfileViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TeacherProfile.objects.select_related('user')
    serializer_class = TeacherProfileSerializer


class TeacherSlotsView(generics.ListAPIView):
    serializer_class = SlotSerializer

    def get_queryset(self):
        teacher_id = self.kwargs['teacher_id']
        if self.request.user.is_teacher_role:
            own_profile = getattr(self.request.user, 'teacher_profile', None)
            if not own_profile or own_profile.id != teacher_id:
                raise exceptions.PermissionDenied('Учитель может смотреть только свои слоты.')
        return Slot.objects.select_related('event', 'teacher', 'teacher__user', 'classroom').filter(teacher_id=teacher_id)


class RegistrationsBySlotView(generics.ListAPIView):
    serializer_class = RegistrationSerializer

    def get_queryset(self):
        slot_id = self.kwargs['slot_id']
        queryset = Registration.objects.select_related('slot', 'slot__event', 'slot__teacher', 'slot__teacher__user', 'user').filter(slot_id=slot_id)
        if self.request.user.is_admin_role:
            return queryset
        if self.request.user.is_teacher_role:
            return queryset.filter(slot__teacher=getattr(self.request.user, 'teacher_profile', None))
        raise exceptions.PermissionDenied('Недостаточно прав.')

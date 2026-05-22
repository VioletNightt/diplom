from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import EmptyRegistrationForm, TeacherSlotForm, TestingRegistrationForm
from .models import Classroom, Event, Registration, Slot, TeacherProfile
from .services import RegistrationError, cancel_registration, create_registration, mark_attendance, notify_slot_change


def home_page(request):
    counters = {
        event_type: Slot.objects.filter(
            event__event_type=event_type,
            event__is_active=True,
            status=Slot.Status.OPEN,
            start_time__gt=timezone.now(),
        ).count()
        for event_type, _ in Event.EventType.choices
    }
    return render(request, 'events/home.html', {'counters': counters})


def event_type_page(request, event_type):
    if event_type not in Event.EventType.values:
        return redirect('home')
    slots = Slot.objects.select_related('event', 'teacher', 'teacher__user', 'classroom').filter(
        event__event_type=event_type,
        event__is_active=True,
        start_time__gt=timezone.now(),
    ).prefetch_related('available_classes')
    if not request.user.is_staff:
        slots = slots.exclude(status=Slot.Status.CANCELED)
    if request.user.is_authenticated and not request.user.is_admin_role and not request.user.is_teacher_role:
        user_class = request.user.school_class
        if user_class:
            slots = slots.filter(Q(available_classes__isnull=True) | Q(available_classes=user_class)).distinct()
        else:
            slots = slots.filter(available_classes__isnull=True)

    query = request.GET.get('q', '').strip()
    if query:
        slots = slots.filter(
            Q(event__title__icontains=query)
            | Q(subject__icontains=query)
            | Q(target_class__icontains=query)
            | Q(teacher__user__full_name__icontains=query)
        )
    return render(
        request,
        'events/event_type.html',
        {
            'event_type': event_type,
            'event_type_label': Event.EventType(event_type).label,
            'slots': slots,
            'query': query,
        },
    )


@login_required
def register_slot_page(request, slot_id):
    if request.user.is_admin_role or request.user.is_teacher_role:
        messages.error(request, 'Запись доступна только пользователям/родителям.')
        return redirect('teacher-dashboard' if request.user.is_teacher_role else 'admin:index')
    slot = get_object_or_404(
        Slot.objects.select_related('event', 'teacher', 'teacher__user', 'classroom').prefetch_related('available_classes'),
        pk=slot_id,
    )
    if slot.available_classes.exists() and request.user.school_class not in slot.available_classes.all():
        messages.error(request, 'Этот слот недоступен для вашего класса.')
        return redirect('event-type', event_type=slot.event.event_type)
    form_class = TestingRegistrationForm if slot.event.event_type == Event.EventType.TESTING else EmptyRegistrationForm
    form = form_class(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data.copy()
        data.pop('confirm', None)
        try:
            create_registration(user=request.user, slot_id=slot.id, registration_data=data)
            messages.success(request, 'Запись успешно создана.')
            return redirect('dashboard')
        except RegistrationError as exc:
            messages.error(request, str(exc))
    return render(request, 'events/register_slot.html', {'slot': slot, 'form': form})


@login_required
def dashboard_page(request):
    if request.user.is_admin_role:
        messages.error(request, 'Администратору раздел "Мои записи" недоступен.')
        return redirect('admin:index')
    if request.user.is_teacher_role:
        messages.error(request, 'Учителю раздел "Мои записи" недоступен.')
        return redirect('teacher-dashboard')
    registrations = Registration.objects.select_related('slot', 'slot__event', 'slot__teacher', 'slot__teacher__user', 'slot__classroom').filter(
        user=request.user
    )
    active = registrations.filter(status=Registration.Status.REGISTERED, slot__start_time__gte=timezone.now())
    history = registrations.exclude(id__in=active.values('id'))
    return render(request, 'events/dashboard.html', {'active': active, 'history': history})


@login_required
def cancel_registration_page(request, registration_id):
    registration = get_object_or_404(Registration, pk=registration_id, user=request.user)
    if request.method == 'POST':
        cancel_registration(registration)
        messages.success(request, 'Запись отменена, место освобождено.')
    return redirect('dashboard')


@login_required
def teacher_dashboard_page(request):
    if not request.user.is_teacher_role and not request.user.is_admin_role:
        messages.error(request, 'Раздел доступен только учителям и администраторам.')
        return redirect('home')
    teacher_profile = None
    if request.user.is_teacher_role:
        teacher_profile, _ = TeacherProfile.objects.get_or_create(user=request.user)
    slots = Slot.objects.select_related('event', 'teacher', 'teacher__user', 'classroom').prefetch_related('available_classes')
    if request.user.is_teacher_role and not request.user.is_admin_role:
        slots = slots.filter(teacher=teacher_profile)
    slots = slots.order_by('start_time')
    return render(request, 'events/teacher_dashboard.html', {'slots': slots})


@login_required
def teacher_slot_create_page(request):
    if not request.user.is_teacher_role:
        messages.error(request, 'Создавать слоты может только учитель.')
        return redirect('teacher-dashboard')
    teacher_profile, _ = TeacherProfile.objects.get_or_create(user=request.user)
    form = TeacherSlotForm(request.POST or None)
    form.instance.teacher = teacher_profile
    if request.method == 'POST' and form.is_valid():
        slot = form.save(commit=False)
        slot.max_participants = slot.max_participants or 1
        slot.full_clean()
        slot.save()
        messages.success(request, 'Слот встречи создан.')
        return redirect('teacher-dashboard')
    classrooms = list(
        Classroom.objects.filter(is_active=True)
        .order_by('floor', 'number')
        .values('id', 'floor', 'number', 'capacity')
    )
    return render(request, 'events/teacher_slot_form.html', {'form': form, 'classrooms': classrooms})


@login_required
def teacher_slot_edit_page(request, slot_id):
    slot = get_object_or_404(Slot.objects.select_related('teacher', 'event', 'classroom'), pk=slot_id)
    if not (request.user.is_admin_role or (request.user.is_teacher_role and slot.teacher_id and slot.teacher.user_id == request.user.id)):
        messages.error(request, 'Недостаточно прав.')
        return redirect('teacher-dashboard')
    old_start = slot.start_time
    old_end = slot.end_time
    old_classroom = slot.classroom
    form = TeacherSlotForm(request.POST or None, instance=slot)
    if slot.teacher_id:
        form.instance.teacher = slot.teacher
    if request.method == 'POST' and form.is_valid():
        updated_slot = form.save(commit=False)
        updated_slot.full_clean()
        updated_slot.save()
        changed = (
            old_start != updated_slot.start_time
            or old_end != updated_slot.end_time
            or old_classroom != updated_slot.classroom
        )
        if changed:
            notify_slot_change(
                updated_slot,
                subject=f'Изменение встречи: {updated_slot.event.title}',
                message='Параметры вашей записи были изменены. Проверьте новую дату, время и кабинет.',
            )
        messages.success(request, 'Слот обновлен.')
        return redirect('teacher-dashboard')
    classrooms = list(
        Classroom.objects.filter(is_active=True)
        .order_by('floor', 'number')
        .values('id', 'floor', 'number', 'capacity')
    )
    return render(request, 'events/teacher_slot_form.html', {'form': form, 'classrooms': classrooms, 'slot': slot})


@login_required
def teacher_slot_cancel_page(request, slot_id):
    slot = get_object_or_404(Slot.objects.select_related('teacher', 'event'), pk=slot_id)
    if not (request.user.is_admin_role or (request.user.is_teacher_role and slot.teacher_id and slot.teacher.user_id == request.user.id)):
        messages.error(request, 'Недостаточно прав.')
        return redirect('teacher-dashboard')
    if request.method == 'POST':
        slot.status = Slot.Status.CANCELED
        slot.save(update_fields=['status'])
        notify_slot_change(
            slot,
            subject=f'Отмена встречи: {slot.event.title}',
            message='Ваша запись отменена, потому что встреча была отменена учителем или администратором.',
        )
        Registration.objects.filter(slot=slot, status=Registration.Status.REGISTERED).update(
            status=Registration.Status.CANCELED
        )
        slot.current_participants = 0
        slot.save(update_fields=['current_participants'])
        messages.success(request, 'Встреча отменена, участникам отправлены уведомления.')
    return redirect('teacher-dashboard')


@login_required
def teacher_attendance_page(request, registration_id, value):
    registration = get_object_or_404(Registration.objects.select_related('slot', 'slot__teacher'), pk=registration_id)
    allowed = request.user.is_admin_role or (
        request.user.is_teacher_role
        and registration.slot.teacher_id
        and registration.slot.teacher.user_id == request.user.id
    )
    if not allowed:
        messages.error(request, 'Недостаточно прав.')
        return redirect('teacher-dashboard')
    if request.method == 'POST':
        mark_attendance(registration, value == 'yes')
        messages.success(request, 'Явка обновлена.')
    return redirect('teacher-dashboard')

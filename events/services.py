from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from django.conf import settings
from notifications_app.models import Notification

from .models import Event, Registration, Slot


class RegistrationError(ValueError):
    pass


def validate_registration_payload(slot, registration_data):
    if slot.event.event_type != Event.EventType.TESTING:
        return
    required = {
        'student_full_name': 'ФИО ученика',
        'parent_full_name': 'ФИО родителя',
        'parent_phone': 'Контактный телефон родителя',
    }
    missing = [label for key, label in required.items() if not str(registration_data.get(key, '')).strip()]
    if missing:
        raise RegistrationError('Заполните обязательные поля: ' + ', '.join(missing))


@transaction.atomic
def create_registration(*, user, slot_id, registration_data=None):
    registration_data = registration_data or {}
    slot = Slot.objects.select_for_update().select_related('event').get(pk=slot_id)
    if not slot.is_available:
        raise RegistrationError('В выбранном слоте нет свободных мест или он недоступен.')
    if Registration.objects.filter(slot=slot, user=user, status=Registration.Status.REGISTERED).exists():
        raise RegistrationError('Вы уже записаны на этот слот.')
    validate_registration_payload(slot, registration_data)

    registration = Registration.objects.create(
        slot=slot,
        user=user,
        registration_data=registration_data,
        status=Registration.Status.REGISTERED,
    )
    slot.current_participants += 1
    if slot.current_participants >= slot.max_participants:
        slot.status = Slot.Status.CLOSED
    slot.save(update_fields=['current_participants', 'status'])
    send_registration_notification(registration, Notification.Type.CONFIRMATION)
    return registration


@transaction.atomic
def cancel_registration(registration):
    registration = Registration.objects.select_for_update().select_related('slot', 'slot__event').get(pk=registration.pk)
    if registration.status != Registration.Status.REGISTERED:
        return registration
    registration.status = Registration.Status.CANCELED
    registration.save(update_fields=['status'])
    slot = Slot.objects.select_for_update().get(pk=registration.slot_id)
    slot.current_participants = max(slot.current_participants - 1, 0)
    if slot.status == Slot.Status.CLOSED and slot.start_time > timezone.now() and slot.event.is_active:
        slot.status = Slot.Status.OPEN
    slot.save(update_fields=['current_participants', 'status'])
    return registration


def mark_attendance(registration, attended):
    registration.status = Registration.Status.ATTENDED if attended else Registration.Status.NO_SHOW
    registration.attended_at = timezone.now() if attended else None
    registration.save(update_fields=['status', 'attended_at'])
    return registration


def send_registration_notification(registration, notification_type):
    subject = f'Регистрация: {registration.slot.event.title}'
    message = (
        f'Здравствуйте, {registration.user.full_name}!\n\n'
        f'Ваша запись на "{registration.slot.event.title}" подтверждена.\n'
        f'Дата и время: {registration.slot.start_time:%d.%m.%Y %H:%M}.\n'
        f'Кабинет: {registration.slot.classroom or "не указан"}.\n'
    )
    status = Notification.Status.SENT
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [registration.user.email], fail_silently=False)
    except Exception as exc:
        status = Notification.Status.FAILED
        message = f'{message}\nОшибка отправки: {exc}'
    Notification.objects.create(
        user=registration.user,
        registration=registration,
        type=notification_type,
        status=status,
        message=message,
    )


def notify_slot_change(slot, *, subject, message):
    registrations = Registration.objects.select_related('user').filter(
        slot=slot,
        status=Registration.Status.REGISTERED,
    )
    for registration in registrations:
        full_message = (
            f'Здравствуйте, {registration.user.full_name}!\n\n'
            f'{message}\n\n'
            f'Мероприятие: {slot.event.title}\n'
            f'Дата и время: {slot.start_time:%d.%m.%Y %H:%M}\n'
            f'Кабинет: {slot.classroom or "не указан"}.\n'
        )
        status = Notification.Status.SENT
        try:
            send_mail(subject, full_message, settings.DEFAULT_FROM_EMAIL, [registration.user.email], fail_silently=False)
        except Exception as exc:
            status = Notification.Status.FAILED
            full_message = f'{full_message}\nОшибка отправки: {exc}'
        Notification.objects.create(
            user=registration.user,
            registration=registration,
            type=Notification.Type.CHANGE,
            status=status,
            message=full_message,
        )

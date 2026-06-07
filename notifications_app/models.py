from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    class Type(models.TextChoices):
        CONFIRMATION = 'confirmation', _('Подтверждение')
        REMINDER = 'reminder', _('Напоминание')
        CHANGE = 'change', _('Изменение')

    class Status(models.TextChoices):
        SENT = 'sent', _('Отправлено')
        FAILED = 'failed', _('Ошибка')

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    registration = models.ForeignKey('events.Registration', on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=50, choices=Type.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SENT)
    message = models.TextField(blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sent_at']
        verbose_name = _('Уведомление')
        verbose_name_plural = _('Уведомления')

    def __str__(self):
        return f'{self.get_type_display()} для {self.registration.participant_email}'

# Create your models here.

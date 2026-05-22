from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class TeacherProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='teacher_profile',
        verbose_name=_('Пользователь'),
    )
    subject = models.CharField(_('Предмет'), max_length=100, blank=True)
    department = models.CharField(_('Кафедра/отделение'), max_length=100, blank=True)

    class Meta:
        verbose_name = _('Профиль учителя')
        verbose_name_plural = _('Профили учителей')

    def clean(self):
        if self.user_id and self.user.role != 'teacher':
            raise ValidationError(_('Профиль учителя можно привязать только к пользователю с ролью teacher.'))

    def __str__(self):
        return self.user.full_name


class Event(models.Model):
    class EventType(models.TextChoices):
        EXAM = 'exam', _('Пробный экзамен')
        TESTING = 'testing', _('Входное тестирование')
        MEETING = 'meeting', _('Встреча с учителем')

    title = models.CharField(_('Название'), max_length=255)
    event_type = models.CharField(_('Тип'), max_length=20, choices=EventType.choices)
    description = models.TextField(_('Описание'), blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_events',
        verbose_name=_('Создал'),
    )
    is_active = models.BooleanField(_('Активно'), default=True)
    created_at = models.DateTimeField(_('Создано'), auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Мероприятие')
        verbose_name_plural = _('Мероприятия')

    def __str__(self):
        return self.title


class SchoolClass(models.Model):
    name = models.CharField(_('Название класса'), max_length=20, unique=True)
    is_active = models.BooleanField(_('Активен'), default=True)

    class Meta:
        ordering = ['name']
        verbose_name = _('Класс')
        verbose_name_plural = _('Классы')

    def __str__(self):
        return self.name


class Classroom(models.Model):
    floor = models.PositiveSmallIntegerField(_('Этаж'))
    number = models.CharField(_('Номер кабинета'), max_length=20)
    capacity = models.PositiveIntegerField(_('Количество мест'))
    is_active = models.BooleanField(_('Активен'), default=True)

    class Meta:
        ordering = ['floor', 'number']
        constraints = [
            models.UniqueConstraint(fields=['floor', 'number'], name='unique_classroom_floor_number')
        ]
        verbose_name = _('Кабинет')
        verbose_name_plural = _('Кабинеты')

    def clean(self):
        if self.capacity < 1:
            raise ValidationError(_('Количество мест должно быть больше нуля.'))

    def __str__(self):
        return f'Кабинет {self.number}, {self.floor} этаж ({self.capacity} мест)'


class Slot(models.Model):
    class Status(models.TextChoices):
        OPEN = 'open', _('Открыт')
        CLOSED = 'closed', _('Закрыт')
        CANCELED = 'canceled', _('Отменен')

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='slots', verbose_name=_('Мероприятие'))
    teacher = models.ForeignKey(
        TeacherProfile,
        on_delete=models.PROTECT,
        related_name='slots',
        verbose_name=_('Учитель'),
        null=True,
        blank=True,
    )
    subject = models.CharField(_('Предмет'), max_length=100, blank=True)
    target_class = models.CharField(_('Класс поступления'), max_length=10, blank=True)
    available_classes = models.ManyToManyField(
        SchoolClass,
        blank=True,
        related_name='slots',
        verbose_name=_('Доступно классам'),
        help_text=_('Если классы не выбраны, слот доступен всем.'),
    )
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.PROTECT,
        related_name='slots',
        verbose_name=_('Кабинет'),
        null=True,
        blank=True,
    )
    start_time = models.DateTimeField(_('Начало'))
    end_time = models.DateTimeField(_('Окончание'))
    max_participants = models.PositiveIntegerField(_('Максимум мест'), default=1)
    current_participants = models.PositiveIntegerField(_('Текущее количество'), default=0)
    status = models.CharField(_('Статус'), max_length=20, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(_('Создано'), auto_now_add=True)

    class Meta:
        ordering = ['start_time']
        indexes = [
            models.Index(fields=['event', 'status', 'start_time']),
            models.Index(fields=['teacher', 'start_time']),
            models.Index(fields=['subject']),
            models.Index(fields=['target_class']),
        ]
        verbose_name = _('Слот')
        verbose_name_plural = _('Слоты')

    def clean(self):
        if self.end_time <= self.start_time:
            raise ValidationError(_('Время окончания должно быть позже времени начала.'))
        if self.max_participants < 1:
            raise ValidationError(_('Количество мест должно быть больше нуля.'))
        event_type = self.event.event_type if self.event_id else None
        if event_type == Event.EventType.EXAM and not self.subject:
            raise ValidationError(_('Для пробного экзамена нужно указать предмет.'))
        if event_type == Event.EventType.TESTING and self.target_class not in {'9', '11'}:
            raise ValidationError(_('Для входного тестирования нужно указать класс 9 или 11.'))
        if event_type == Event.EventType.MEETING and not self.teacher_id:
            raise ValidationError(_('Для встречи нужно указать учителя.'))
        if self.classroom_id and self.max_participants > self.classroom.capacity:
            raise ValidationError(_('Количество мест слота не может превышать вместимость кабинета.'))

    @property
    def free_places(self):
        return max(self.max_participants - self.current_participants, 0)

    @property
    def is_available(self):
        return self.status == self.Status.OPEN and self.event.is_active and self.free_places > 0 and self.start_time > timezone.now()

    def __str__(self):
        return f'{self.event.title}: {self.start_time:%d.%m.%Y %H:%M}'


class Registration(models.Model):
    class Status(models.TextChoices):
        REGISTERED = 'registered', _('Зарегистрирован')
        ATTENDED = 'attended', _('Присутствовал')
        CANCELED = 'canceled', _('Отменен')
        NO_SHOW = 'no_show', _('Не явился')

    slot = models.ForeignKey(Slot, on_delete=models.CASCADE, related_name='registrations', verbose_name=_('Слот'))
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='registrations',
        verbose_name=_('Пользователь'),
    )
    registration_data = models.JSONField(_('Дополнительные данные'), default=dict, blank=True)
    status = models.CharField(_('Статус'), max_length=20, choices=Status.choices, default=Status.REGISTERED)
    registered_at = models.DateTimeField(_('Дата регистрации'), auto_now_add=True)
    attended_at = models.DateTimeField(_('Дата явки'), null=True, blank=True)

    class Meta:
        ordering = ['-registered_at']
        indexes = [
            models.Index(fields=['slot', 'status']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['registered_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['slot', 'user'],
                condition=models.Q(status='registered'),
                name='unique_active_registration_per_slot_user',
            )
        ]
        verbose_name = _('Регистрация')
        verbose_name_plural = _('Регистрации')

    def __str__(self):
        return f'{self.user.full_name} -> {self.slot}'

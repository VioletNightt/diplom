from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('role', User.Role.USER)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.ADMIN)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', _('Администратор')
        TEACHER = 'teacher', _('Учитель')
        USER = 'user', _('Пользователь')

    username = None
    email = models.EmailField(_('email'), unique=True)
    full_name = models.CharField(_('ФИО'), max_length=255)
    phone = models.CharField(_('Телефон'), max_length=20, blank=True)
    role = models.CharField(_('Роль'), max_length=20, choices=Role.choices, default=Role.USER)
    school_class = models.ForeignKey(
        'events.SchoolClass',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name=_('Класс'),
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']

    objects = UserManager()

    def __str__(self):
        return f'{self.full_name} <{self.email}>'

    @property
    def is_admin_role(self):
        return self.is_superuser or self.role == self.Role.ADMIN

    @property
    def is_teacher_role(self):
        return self.role == self.Role.TEACHER


from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from events.models import TeacherProfile

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ['email']
    list_display = ['email', 'full_name', 'phone', 'role', 'school_class', 'is_active', 'is_staff']
    list_filter = ['role', 'school_class', 'is_active', 'is_staff', 'is_superuser']
    search_fields = ['email', 'full_name', 'phone']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Персональные данные', {'fields': ('full_name', 'phone', 'role', 'school_class')}),
        ('Права доступа', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Важные даты', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'phone', 'role', 'school_class', 'password1', 'password2'),
        }),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.role == User.Role.TEACHER:
            TeacherProfile.objects.get_or_create(user=obj)


try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass

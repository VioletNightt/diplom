from django.contrib import admin
from django.utils import timezone

from .models import Classroom, Event, Registration, SchoolClass, Slot, TeacherProfile
from .services import cancel_registration, mark_attendance


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'subject', 'department']
    search_fields = ['user__full_name', 'user__email', 'subject', 'department']

    class Media:
        js = ('js/admin_russian_plural.js',)


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ['number', 'floor', 'capacity', 'is_active']
    list_filter = ['floor', 'is_active']
    search_fields = ['number']
    ordering = ['floor', 'number']

    class Media:
        js = ('js/admin_russian_plural.js',)


@admin.register(SchoolClass)
class SchoolClassAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']
    ordering = ['name']


class SlotInline(admin.TabularInline):
    model = Slot
    extra = 0
    fields = ['start_time', 'end_time', 'classroom', 'max_participants', 'current_participants', 'status', 'teacher', 'subject', 'target_class']
    readonly_fields = ['current_participants']


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'event_type', 'is_active', 'created_by', 'created_at']
    list_filter = ['event_type', 'is_active', 'created_at']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at']
    inlines = [SlotInline]

    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Slot)
class SlotAdmin(admin.ModelAdmin):
    list_display = ['event', 'start_time', 'end_time', 'classroom', 'classes_display', 'max_participants', 'current_participants', 'free_places', 'status', 'teacher', 'subject', 'target_class']
    list_filter = ['status', 'event__event_type', 'available_classes', 'start_time', 'classroom', 'teacher', 'subject', 'target_class']
    search_fields = ['event__title', 'subject', 'classroom__number', 'teacher__user__full_name']
    readonly_fields = ['current_participants', 'free_places']
    filter_horizontal = ['available_classes']
    date_hierarchy = 'start_time'

    class Media:
        js = ('js/admin_russian_plural.js',)

    @admin.display(description='Классы')
    def classes_display(self, obj):
        classes = list(obj.available_classes.all())
        if not classes:
            return 'Все'
        return ', '.join(item.name for item in classes)


@admin.action(description='Отметить выбранных как присутствовавших')
def mark_attended(modeladmin, request, queryset):
    for registration in queryset.select_related('slot'):
        mark_attendance(registration, True)


@admin.action(description='Отметить выбранных как не явившихся')
def mark_no_show(modeladmin, request, queryset):
    for registration in queryset.select_related('slot'):
        mark_attendance(registration, False)


@admin.action(description='Отменить выбранные регистрации')
def cancel_selected(modeladmin, request, queryset):
    for registration in queryset:
        cancel_registration(registration)


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ['user', 'slot', 'status', 'registered_at', 'attended_at']
    list_filter = ['status', 'slot__event__event_type', 'slot__start_time']
    search_fields = ['user__full_name', 'user__email', 'user__phone', 'slot__event__title']
    readonly_fields = ['registered_at', 'attended_at']
    date_hierarchy = 'registered_at'
    actions = [mark_attended, mark_no_show, cancel_selected]

    def save_model(self, request, obj, form, change):
        if obj.status == Registration.Status.ATTENDED and not obj.attended_at:
            obj.attended_at = timezone.now()
        super().save_model(request, obj, form, change)

# Register your models here.

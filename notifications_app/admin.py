from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'registration', 'type', 'status', 'sent_at']
    list_filter = ['type', 'status', 'sent_at']
    search_fields = ['user__email', 'user__full_name', 'message']
    readonly_fields = ['user', 'registration', 'type', 'status', 'message', 'sent_at']

# Register your models here.

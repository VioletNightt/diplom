from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['recipient_email', 'user', 'registration', 'type', 'status', 'sent_at']
    list_filter = ['type', 'status', 'sent_at']
    search_fields = ['user__email', 'user__full_name', 'registration__guest_email', 'registration__guest_full_name', 'message']
    readonly_fields = ['user', 'registration', 'type', 'status', 'message', 'sent_at']

    @admin.display(description='Email')
    def recipient_email(self, obj):
        return obj.registration.participant_email

# Register your models here.

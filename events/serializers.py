from rest_framework import serializers

from accounts.models import User

from .models import Classroom, Event, Registration, SchoolClass, Slot, TeacherProfile


class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'phone', 'role']


class TeacherProfileSerializer(serializers.ModelSerializer):
    user = UserSummarySerializer(read_only=True)

    class Meta:
        model = TeacherProfile
        fields = ['id', 'user', 'subject', 'department']


class ClassroomSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()

    class Meta:
        model = Classroom
        fields = ['id', 'floor', 'number', 'capacity', 'is_active', 'label']

    def get_label(self, obj):
        return str(obj)


class SchoolClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolClass
        fields = ['id', 'name', 'is_active']


class EventSerializer(serializers.ModelSerializer):
    created_by = UserSummarySerializer(read_only=True)

    class Meta:
        model = Event
        fields = ['id', 'title', 'event_type', 'description', 'created_by', 'is_active', 'created_at']
        read_only_fields = ['created_by', 'created_at']


class SlotSerializer(serializers.ModelSerializer):
    event_title = serializers.CharField(source='event.title', read_only=True)
    event_type = serializers.CharField(source='event.event_type', read_only=True)
    teacher_name = serializers.CharField(source='teacher.user.full_name', read_only=True)
    classroom_label = serializers.SerializerMethodField()
    free_places = serializers.IntegerField(read_only=True)
    is_available = serializers.BooleanField(read_only=True)

    class Meta:
        model = Slot
        fields = [
            'id',
            'event',
            'event_title',
            'event_type',
            'teacher',
            'teacher_name',
            'classroom',
            'classroom_label',
            'available_classes',
            'subject',
            'target_class',
            'start_time',
            'end_time',
            'max_participants',
            'current_participants',
            'free_places',
            'status',
            'is_available',
        ]
        read_only_fields = ['current_participants', 'free_places', 'is_available']

    def get_classroom_label(self, obj):
        return str(obj.classroom) if obj.classroom_id else ''

    def validate(self, attrs):
        instance = self.instance or Slot()
        for key, value in attrs.items():
            setattr(instance, key, value)
        instance.clean()
        return attrs


class RegistrationSerializer(serializers.ModelSerializer):
    user = UserSummarySerializer(read_only=True)
    slot_detail = SlotSerializer(source='slot', read_only=True)
    participant_full_name = serializers.CharField(read_only=True)
    participant_email = serializers.CharField(read_only=True)
    participant_school_class = SchoolClassSerializer(read_only=True)

    class Meta:
        model = Registration
        fields = [
            'id',
            'slot',
            'slot_detail',
            'user',
            'guest_full_name',
            'guest_email',
            'guest_school_class',
            'participant_full_name',
            'participant_email',
            'participant_school_class',
            'registration_data',
            'status',
            'registered_at',
            'attended_at',
        ]
        read_only_fields = ['user', 'status', 'registered_at', 'attended_at']


class RegistrationCreateSerializer(serializers.Serializer):
    slot = serializers.IntegerField()
    registration_data = serializers.JSONField(required=False)
    guest_full_name = serializers.CharField(required=False, allow_blank=True)
    guest_email = serializers.EmailField(required=False, allow_blank=True)
    guest_school_class = serializers.PrimaryKeyRelatedField(
        queryset=SchoolClass.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )


class AttendanceSerializer(serializers.Serializer):
    attended = serializers.BooleanField()

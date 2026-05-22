from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from events.models import Classroom, Event, SchoolClass, Slot, TeacherProfile


class Command(BaseCommand):
    help = 'Create demo users, events, and slots for local development.'

    def handle(self, *args, **options):
        admin, created = User.objects.get_or_create(
            email='admin@example.com',
            defaults={
                'full_name': 'Администратор школы',
                'role': User.Role.ADMIN,
                'is_staff': True,
                'is_superuser': True,
            },
        )
        if created:
            admin.set_password('admin12345')
            admin.save()

        teacher_user, created = User.objects.get_or_create(
            email='teacher@example.com',
            defaults={
                'full_name': 'Иванова Мария Сергеевна',
                'role': User.Role.TEACHER,
                'phone': '+7 900 100-20-30',
            },
        )
        if created:
            teacher_user.set_password('teacher12345')
            teacher_user.save()

        parent, created = User.objects.get_or_create(
            email='parent@example.com',
            defaults={
                'full_name': 'Петров Алексей Викторович',
                'role': User.Role.USER,
                'phone': '+7 900 555-10-10',
            },
        )
        if created:
            parent.set_password('parent12345')
            parent.save()

        class_1a, _ = SchoolClass.objects.get_or_create(name='1А')
        class_5b, _ = SchoolClass.objects.get_or_create(name='5Б')
        class_9a, _ = SchoolClass.objects.get_or_create(name='9А')
        class_11a, _ = SchoolClass.objects.get_or_create(name='11А')
        if not parent.school_class_id:
            parent.school_class = class_9a
            parent.save(update_fields=['school_class'])

        teacher, _ = TeacherProfile.objects.get_or_create(
            user=teacher_user,
            defaults={'subject': 'Математика', 'department': 'Основная школа'},
        )

        room_101, _ = Classroom.objects.get_or_create(
            floor=1,
            number='101',
            defaults={'capacity': 25},
        )
        room_204, _ = Classroom.objects.get_or_create(
            floor=2,
            number='204',
            defaults={'capacity': 20},
        )
        room_305, _ = Classroom.objects.get_or_create(
            floor=3,
            number='305',
            defaults={'capacity': 1},
        )

        exam, _ = Event.objects.get_or_create(
            title='Пробный экзамен по математике',
            event_type=Event.EventType.EXAM,
            defaults={'created_by': admin, 'description': 'Подготовительный пробный экзамен.'},
        )
        testing, _ = Event.objects.get_or_create(
            title='Входное тестирование',
            event_type=Event.EventType.TESTING,
            defaults={'created_by': admin, 'description': 'Тестирование для поступающих.'},
        )
        meeting, _ = Event.objects.get_or_create(
            title='Индивидуальная встреча с учителем',
            event_type=Event.EventType.MEETING,
            defaults={'created_by': admin, 'description': 'Очная консультация.'},
        )

        base = timezone.now().replace(minute=0, second=0, microsecond=0) + timedelta(days=3)
        slots = [
            {
                'event': exam,
                'subject': 'Математика',
                'classroom': room_101,
                'start_time': base,
                'end_time': base + timedelta(hours=2),
                'max_participants': 25,
            },
            {
                'event': testing,
                'target_class': '9',
                'classroom': room_204,
                'start_time': base + timedelta(days=1),
                'end_time': base + timedelta(days=1, hours=1),
                'max_participants': 20,
            },
            {
                'event': testing,
                'target_class': '11',
                'classroom': room_204,
                'start_time': base + timedelta(days=2),
                'end_time': base + timedelta(days=2, hours=1),
                'max_participants': 20,
            },
            {
                'event': meeting,
                'teacher': teacher,
                'classroom': room_305,
                'start_time': base + timedelta(days=3),
                'end_time': base + timedelta(days=3, minutes=30),
                'max_participants': 1,
            },
        ]
        for slot_data in slots:
            slot, _ = Slot.objects.update_or_create(
                event=slot_data['event'],
                start_time=slot_data['start_time'],
                defaults=slot_data,
            )
            if slot.event.event_type == Event.EventType.TESTING and slot.target_class == '9':
                slot.available_classes.set([class_9a])
            elif slot.event.event_type == Event.EventType.TESTING and slot.target_class == '11':
                slot.available_classes.set([class_11a])
            elif slot.event.event_type == Event.EventType.MEETING:
                slot.available_classes.set([class_1a, class_5b, class_9a, class_11a])

        Slot.objects.filter(event__event_type=Event.EventType.EXAM, classroom__isnull=True).update(classroom=room_101)
        Slot.objects.filter(event__event_type=Event.EventType.TESTING, classroom__isnull=True).update(classroom=room_204)
        Slot.objects.filter(event__event_type=Event.EventType.MEETING, classroom__isnull=True).update(classroom=room_305)

        self.stdout.write(self.style.SUCCESS('Demo data created.'))

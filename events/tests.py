from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from accounts.models import User
from notifications_app.models import Notification

from .models import Classroom, Event, Registration, SchoolClass, Slot, TeacherProfile
from .services import RegistrationError, cancel_registration, create_registration


class RegistrationServiceTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email='admin@example.com',
            password='password123',
            full_name='Администратор',
        )
        self.user = User.objects.create_user(
            email='parent@example.com',
            password='password123',
            full_name='Родитель',
            phone='+79990000000',
        )
        self.event = Event.objects.create(
            title='Пробный экзамен',
            event_type=Event.EventType.EXAM,
            created_by=self.admin,
        )
        self.slot = Slot.objects.create(
            event=self.event,
            subject='Математика',
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1, hours=2),
            max_participants=1,
        )

    def test_create_registration_closes_full_slot(self):
        registration = create_registration(user=self.user, slot_id=self.slot.id)
        self.slot.refresh_from_db()
        self.assertEqual(registration.status, Registration.Status.REGISTERED)
        self.assertEqual(self.slot.current_participants, 1)
        self.assertEqual(self.slot.status, Slot.Status.CLOSED)

    def test_create_registration_rejects_full_slot(self):
        create_registration(user=self.user, slot_id=self.slot.id)
        second_user = User.objects.create_user(
            email='second@example.com',
            password='password123',
            full_name='Второй пользователь',
        )
        with self.assertRaises(RegistrationError):
            create_registration(user=second_user, slot_id=self.slot.id)

    def test_cancel_registration_reopens_slot(self):
        registration = create_registration(user=self.user, slot_id=self.slot.id)
        cancel_registration(registration)
        self.slot.refresh_from_db()
        registration.refresh_from_db()
        self.assertEqual(registration.status, Registration.Status.CANCELED)
        self.assertEqual(self.slot.current_participants, 0)
        self.assertEqual(self.slot.status, Slot.Status.OPEN)

    def test_testing_registration_requires_parent_data(self):
        testing = Event.objects.create(
            title='Входное тестирование',
            event_type=Event.EventType.TESTING,
            created_by=self.admin,
        )
        slot = Slot.objects.create(
            event=testing,
            target_class='9',
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1, hours=1),
            max_participants=10,
        )
        with self.assertRaises(RegistrationError):
            create_registration(user=self.user, slot_id=slot.id, registration_data={})


class ApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            email='admin@example.com',
            password='password123',
            full_name='Администратор',
        )
        self.teacher_user = User.objects.create_user(
            email='teacher@example.com',
            password='password123',
            full_name='Учитель',
            role=User.Role.TEACHER,
        )
        self.teacher = TeacherProfile.objects.create(user=self.teacher_user, subject='Русский язык')
        self.user = User.objects.create_user(
            email='parent@example.com',
            password='password123',
            full_name='Родитель',
        )
        self.event = Event.objects.create(
            title='Встреча',
            event_type=Event.EventType.MEETING,
            created_by=self.admin,
        )
        self.classroom = Classroom.objects.create(floor=1, number='101', capacity=20)
        self.slot = Slot.objects.create(
            event=self.event,
            teacher=self.teacher,
            classroom=self.classroom,
            start_time=timezone.now() + timedelta(days=2),
            end_time=timezone.now() + timedelta(days=2, minutes=30),
            max_participants=1,
        )

    def authenticate(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_user_can_register_via_api(self):
        self.authenticate(self.user)
        response = self.client.post('/api/registrations/', {'slot': self.slot.id}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Registration.objects.count(), 1)

    def test_teacher_can_mark_attendance(self):
        registration = create_registration(user=self.user, slot_id=self.slot.id)
        self.authenticate(self.teacher_user)
        response = self.client.post(
            f'/api/registrations/{registration.id}/attendance/',
            {'attended': True},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        registration.refresh_from_db()
        self.assertEqual(registration.status, Registration.Status.ATTENDED)

    def test_admin_can_export_xlsx(self):
        create_registration(user=self.user, slot_id=self.slot.id)
        self.authenticate(self.admin)
        response = self.client.get('/api/reports/?format=xlsx')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

    def test_admin_can_export_statistics_xlsx(self):
        create_registration(user=self.user, slot_id=self.slot.id)
        self.authenticate(self.admin)
        response = self.client.get('/api/reports/statistics/?format=xlsx')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )


class FrontendTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email='admin@example.com',
            password='password123',
            full_name='Администратор',
        )
        self.user = User.objects.create_user(
            email='parent@example.com',
            password='password123',
            full_name='Родитель',
        )
        self.event = Event.objects.create(
            title='Входное тестирование',
            event_type=Event.EventType.TESTING,
            created_by=self.admin,
        )
        self.slot = Slot.objects.create(
            event=self.event,
            target_class='9',
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1, hours=1),
            max_participants=3,
        )

    def test_teacher_can_create_slot_with_classroom_from_frontend(self):
        teacher_user = User.objects.create_user(
            email='teacher@example.com',
            password='password123',
            full_name='Учитель',
            role=User.Role.TEACHER,
        )
        TeacherProfile.objects.create(user=teacher_user, subject='Математика')
        meeting = Event.objects.create(
            title='Встреча с учителем',
            event_type=Event.EventType.MEETING,
            created_by=self.admin,
        )
        classroom = Classroom.objects.create(floor=2, number='204', capacity=5)
        self.client.login(username='teacher@example.com', password='password123')
        start = timezone.now() + timedelta(days=2)
        response = self.client.post(
            '/teacher/slots/new/',
            {
                'event': meeting.id,
                'classroom': classroom.id,
                'start_time': start.strftime('%Y-%m-%dT%H:%M'),
                'end_time': (start + timedelta(minutes=30)).strftime('%Y-%m-%dT%H:%M'),
                'max_participants': 1,
            },
            follow=True,
        )
        self.assertContains(response, 'Слот встречи создан')
        self.assertTrue(Slot.objects.filter(event=meeting, classroom=classroom, teacher__user=teacher_user).exists())

    def test_teacher_slot_rejects_capacity_over_classroom_limit(self):
        teacher_user = User.objects.create_user(
            email='teacher-over-capacity@example.com',
            password='password123',
            full_name='Учитель',
            role=User.Role.TEACHER,
        )
        TeacherProfile.objects.create(user=teacher_user, subject='Математика')
        meeting = Event.objects.create(
            title='Встреча с учителем',
            event_type=Event.EventType.MEETING,
            created_by=self.admin,
        )
        classroom = Classroom.objects.create(floor=3, number='305', capacity=1)
        self.client.login(username='teacher-over-capacity@example.com', password='password123')
        start = timezone.now() + timedelta(days=2)
        response = self.client.post(
            '/teacher/slots/new/',
            {
                'event': meeting.id,
                'classroom': classroom.id,
                'start_time': start.strftime('%Y-%m-%dT%H:%M'),
                'end_time': (start + timedelta(minutes=30)).strftime('%Y-%m-%dT%H:%M'),
                'max_participants': 500,
            },
        )
        self.assertContains(response, 'Количество мест слота не может превышать вместимость кабинета', status_code=200)
        self.assertFalse(Slot.objects.filter(event=meeting, classroom=classroom, max_participants=500).exists())

    def test_teacher_without_profile_gets_profile_when_opening_slot_form(self):
        teacher_user = User.objects.create_user(
            email='teacher-no-profile@example.com',
            password='password123',
            full_name='Учитель без профиля',
            role=User.Role.TEACHER,
        )
        self.assertFalse(TeacherProfile.objects.filter(user=teacher_user).exists())
        self.client.login(username='teacher-no-profile@example.com', password='password123')
        response = self.client.get('/teacher/slots/new/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(TeacherProfile.objects.filter(user=teacher_user).exists())

    def test_home_page_renders(self):
        response = self.client.get('/')
        self.assertContains(response, 'Выберите тип записи')
        self.assertContains(response, 'Входное тестирование')

    def test_event_type_page_renders_slots(self):
        response = self.client.get('/events/testing/')
        self.assertContains(response, self.event.title)
        self.assertContains(response, 'Класс 9')

    def test_user_can_register_from_frontend(self):
        self.client.login(username='parent@example.com', password='password123')
        response = self.client.post(
            f'/slots/{self.slot.id}/register/',
            {
                'student_full_name': 'Петров Петр',
                'parent_full_name': 'Петров Алексей',
                'parent_phone': '+79995551010',
            },
            follow=True,
        )
        self.assertContains(response, 'Запись успешно создана')
        self.assertEqual(Registration.objects.filter(user=self.user, slot=self.slot).count(), 1)
        self.assertTrue(Notification.objects.filter(user=self.user, type=Notification.Type.CONFIRMATION).exists())

    def test_teacher_can_edit_meeting_and_notify_participants(self):
        teacher_user = User.objects.create_user(
            email='teacher-edit@example.com',
            password='password123',
            full_name='Учитель',
            role=User.Role.TEACHER,
        )
        teacher = TeacherProfile.objects.create(user=teacher_user)
        meeting = Event.objects.create(
            title='Встреча с учителем',
            event_type=Event.EventType.MEETING,
            created_by=self.admin,
        )
        classroom = Classroom.objects.create(floor=1, number='101', capacity=10)
        new_classroom = Classroom.objects.create(floor=2, number='202', capacity=10)
        start = timezone.now() + timedelta(days=2)
        slot = Slot.objects.create(
            event=meeting,
            teacher=teacher,
            classroom=classroom,
            start_time=start,
            end_time=start + timedelta(minutes=30),
            max_participants=2,
        )
        create_registration(user=self.user, slot_id=slot.id)
        self.client.login(username='teacher-edit@example.com', password='password123')
        new_start = start + timedelta(days=1)
        response = self.client.post(
            f'/teacher/slots/{slot.id}/edit/',
            {
                'event': meeting.id,
                'classroom': new_classroom.id,
                'start_time': new_start.strftime('%Y-%m-%dT%H:%M'),
                'end_time': (new_start + timedelta(minutes=30)).strftime('%Y-%m-%dT%H:%M'),
                'max_participants': 2,
            },
            follow=True,
        )
        self.assertContains(response, 'Слот обновлен')
        slot.refresh_from_db()
        self.assertEqual(slot.classroom, new_classroom)
        self.assertTrue(Notification.objects.filter(user=self.user, type=Notification.Type.CHANGE).exists())

    def test_teacher_can_cancel_meeting_and_notify_participants(self):
        teacher_user = User.objects.create_user(
            email='teacher-cancel@example.com',
            password='password123',
            full_name='Учитель',
            role=User.Role.TEACHER,
        )
        teacher = TeacherProfile.objects.create(user=teacher_user)
        meeting = Event.objects.create(
            title='Встреча с учителем',
            event_type=Event.EventType.MEETING,
            created_by=self.admin,
        )
        classroom = Classroom.objects.create(floor=1, number='103', capacity=10)
        start = timezone.now() + timedelta(days=2)
        slot = Slot.objects.create(
            event=meeting,
            teacher=teacher,
            classroom=classroom,
            start_time=start,
            end_time=start + timedelta(minutes=30),
            max_participants=2,
        )
        registration = create_registration(user=self.user, slot_id=slot.id)
        self.client.login(username='teacher-cancel@example.com', password='password123')
        response = self.client.post(f'/teacher/slots/{slot.id}/cancel/', follow=True)
        self.assertContains(response, 'Встреча отменена')
        slot.refresh_from_db()
        registration.refresh_from_db()
        self.assertEqual(slot.status, Slot.Status.CANCELED)
        self.assertEqual(registration.status, Registration.Status.CANCELED)
        self.assertTrue(Notification.objects.filter(user=self.user, type=Notification.Type.CHANGE).exists())

    def test_teacher_menu_does_not_show_user_registration_links(self):
        teacher_user = User.objects.create_user(
            email='teacher-menu@example.com',
            password='password123',
            full_name='Учитель',
            role=User.Role.TEACHER,
        )
        TeacherProfile.objects.create(user=teacher_user)
        self.client.login(username='teacher-menu@example.com', password='password123')
        response = self.client.get('/teacher/')
        self.assertContains(response, 'Кабинет учителя')
        self.assertNotContains(response, 'Мои записи')
        self.assertNotContains(response, '>Экзамены<')
        self.assertNotContains(response, '>Тестирование<')
        self.assertNotContains(response, '>Учителя<')

    def test_admin_menu_does_not_show_my_registrations(self):
        self.client.login(username='admin@example.com', password='password123')
        response = self.client.get('/teacher/')
        self.assertContains(response, 'Админка')
        self.assertNotContains(response, 'Мои записи')

    def test_admin_and_teacher_dashboard_page_is_unavailable(self):
        self.client.login(username='admin@example.com', password='password123')
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 302)

        teacher_user = User.objects.create_user(
            email='teacher-dashboard-denied@example.com',
            password='password123',
            full_name='Учитель',
            role=User.Role.TEACHER,
        )
        TeacherProfile.objects.create(user=teacher_user)
        self.client.logout()
        self.client.login(username='teacher-dashboard-denied@example.com', password='password123')
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 302)

    def test_admin_and_teacher_do_not_see_register_button_on_slot_list(self):
        self.client.login(username='admin@example.com', password='password123')
        response = self.client.get('/events/testing/')
        self.assertNotContains(response, 'Записаться')

        teacher_user = User.objects.create_user(
            email='teacher-no-button@example.com',
            password='password123',
            full_name='Учитель',
            role=User.Role.TEACHER,
        )
        TeacherProfile.objects.create(user=teacher_user)
        self.client.logout()
        self.client.login(username='teacher-no-button@example.com', password='password123')
        response = self.client.get('/events/testing/')
        self.assertNotContains(response, 'Записаться')

    def test_teacher_and_admin_cannot_register_by_direct_url(self):
        teacher_user = User.objects.create_user(
            email='teacher-direct@example.com',
            password='password123',
            full_name='Учитель',
            role=User.Role.TEACHER,
        )
        TeacherProfile.objects.create(user=teacher_user)
        self.client.login(username='teacher-direct@example.com', password='password123')
        response = self.client.get(f'/slots/{self.slot.id}/register/')
        self.assertEqual(response.status_code, 302)

    def test_user_sees_only_slots_for_own_class_or_all_classes(self):
        class_1a = SchoolClass.objects.create(name='1А')
        class_5b = SchoolClass.objects.create(name='5Б')
        self.user.school_class = class_1a
        self.user.save(update_fields=['school_class'])

        hidden_slot = Slot.objects.create(
            event=self.event,
            target_class='9',
            start_time=timezone.now() + timedelta(days=3),
            end_time=timezone.now() + timedelta(days=3, hours=1),
            max_participants=3,
        )
        hidden_slot.available_classes.set([class_5b])

        visible_slot = Slot.objects.create(
            event=self.event,
            target_class='9',
            start_time=timezone.now() + timedelta(days=4),
            end_time=timezone.now() + timedelta(days=4, hours=1),
            max_participants=3,
        )
        visible_slot.available_classes.set([class_1a])

        self.client.login(username='parent@example.com', password='password123')
        response = self.client.get('/events/testing/')
        self.assertContains(response, visible_slot.start_time.strftime('%d.%m.%Y'))
        self.assertNotContains(response, hidden_slot.start_time.strftime('%d.%m.%Y'))

    def test_user_cannot_register_for_another_class_by_direct_url(self):
        class_1a = SchoolClass.objects.create(name='1А')
        class_5b = SchoolClass.objects.create(name='5Б')
        self.user.school_class = class_1a
        self.user.save(update_fields=['school_class'])
        self.slot.available_classes.set([class_5b])

        self.client.login(username='parent@example.com', password='password123')
        response = self.client.get(f'/slots/{self.slot.id}/register/')
        self.assertEqual(response.status_code, 302)

        self.client.logout()
        self.client.login(username='admin@example.com', password='password123')
        response = self.client.get(f'/slots/{self.slot.id}/register/')
        self.assertEqual(response.status_code, 302)

# Create your tests here.

import csv
from datetime import datetime

from django.http import HttpResponse
from django.db.models import Count, Q
from openpyxl import Workbook
from rest_framework import permissions
from rest_framework.views import APIView

from events.models import Registration


class ReportExportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Registration.objects.select_related('user', 'slot', 'slot__event', 'slot__teacher', 'slot__teacher__user', 'slot__classroom')
        if user.is_teacher_role and not user.is_admin_role:
            queryset = queryset.filter(slot__teacher=getattr(user, 'teacher_profile', None))
        event_type = self.request.query_params.get('event_type')
        teacher_id = self.request.query_params.get('teacher')
        target_class = self.request.query_params.get('target_class')
        start = self.request.query_params.get('start')
        end = self.request.query_params.get('end')
        if event_type:
            queryset = queryset.filter(slot__event__event_type=event_type)
        if teacher_id:
            queryset = queryset.filter(slot__teacher_id=teacher_id)
        if target_class:
            queryset = queryset.filter(slot__target_class=target_class)
        if start:
            queryset = queryset.filter(slot__start_time__date__gte=datetime.fromisoformat(start).date())
        if end:
            queryset = queryset.filter(slot__start_time__date__lte=datetime.fromisoformat(end).date())
        return queryset.order_by('slot__start_time', 'user__full_name')

    def get(self, request):
        if not (request.user.is_admin_role or request.user.is_teacher_role):
            return HttpResponse('Недостаточно прав.', status=403)
        export_format = request.query_params.get('format', 'csv')
        if export_format == 'xlsx':
            return self.export_xlsx()
        return self.export_csv()

    @staticmethod
    def row(registration):
        slot = registration.slot
        teacher_name = slot.teacher.user.full_name if slot.teacher_id else ''
        classroom = str(slot.classroom) if slot.classroom_id else ''
        return [
            registration.id,
            registration.user.full_name,
            registration.user.email,
            registration.user.phone,
            slot.event.title,
            slot.event.get_event_type_display(),
            slot.subject,
            slot.target_class,
            teacher_name,
            classroom,
            slot.start_time.strftime('%d.%m.%Y %H:%M'),
            registration.get_status_display(),
            registration.registered_at.strftime('%d.%m.%Y %H:%M'),
        ]

    @staticmethod
    def report_headers():
        return [
            'ID',
            'ФИО',
            'Email',
            'Телефон',
            'Мероприятие',
            'Тип',
            'Предмет',
            'Класс',
            'Учитель',
            'Кабинет',
            'Дата и время',
            'Статус',
            'Дата регистрации',
        ]

    def export_csv(self):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="registrations.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow(self.report_headers())
        for registration in self.get_queryset():
            writer.writerow(self.row(registration))
        return response

    def export_xlsx(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = 'Регистрации'
        sheet.append(self.report_headers())
        for registration in self.get_queryset():
            sheet.append(self.row(registration))
        for column in sheet.columns:
            max_length = max(len(str(cell.value or '')) for cell in column)
            sheet.column_dimensions[column[0].column_letter].width = min(max(max_length + 2, 12), 45)
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="registrations.xlsx"'
        workbook.save(response)
        return response


class StatisticsExportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not (request.user.is_admin_role or request.user.is_teacher_role):
            return HttpResponse('Недостаточно прав.', status=403)

        queryset = Registration.objects.select_related('slot', 'slot__event', 'slot__teacher')
        if request.user.is_teacher_role and not request.user.is_admin_role:
            queryset = queryset.filter(slot__teacher=getattr(request.user, 'teacher_profile', None))

        rows = queryset.values(
            'slot__event__title',
            'slot__event__event_type',
        ).annotate(
            total=Count('id'),
            registered=Count('id', filter=Q(status=Registration.Status.REGISTERED)),
            attended=Count('id', filter=Q(status=Registration.Status.ATTENDED)),
            canceled=Count('id', filter=Q(status=Registration.Status.CANCELED)),
            no_show=Count('id', filter=Q(status=Registration.Status.NO_SHOW)),
        ).order_by('slot__event__title')

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = 'Статистика'
        sheet.append(['Мероприятие', 'Тип', 'Всего записей', 'Активные', 'Присутствовали', 'Отменены', 'Не явились'])
        for row in rows:
            sheet.append([
                row['slot__event__title'],
                row['slot__event__event_type'],
                row['total'],
                row['registered'],
                row['attended'],
                row['canceled'],
                row['no_show'],
            ])
        for column in sheet.columns:
            max_length = max(len(str(cell.value or '')) for cell in column)
            sheet.column_dimensions[column[0].column_letter].width = min(max(max_length + 2, 12), 45)

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="statistics.xlsx"'
        workbook.save(response)
        return response

from django import forms

from .models import Classroom, Event, Slot


class TestingRegistrationForm(forms.Form):
    student_full_name = forms.CharField(label='ФИО ученика', max_length=255)
    parent_full_name = forms.CharField(label='ФИО родителя', max_length=255)
    parent_phone = forms.CharField(label='Контактный телефон родителя', max_length=20)


class EmptyRegistrationForm(forms.Form):
    confirm = forms.BooleanField(label='Подтверждаю запись', required=True)


class TeacherSlotForm(forms.ModelForm):
    class Meta:
        model = Slot
        fields = ['event', 'classroom', 'available_classes', 'start_time', 'end_time', 'max_participants']
        widgets = {
            'available_classes': forms.CheckboxSelectMultiple,
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['event'].queryset = Event.objects.filter(event_type=Event.EventType.MEETING, is_active=True)
        self.fields['classroom'].queryset = Classroom.objects.filter(is_active=True)
        self.fields['classroom'].required = True
        self.fields['classroom'].widget.attrs['data-capacity-select'] = '1'
        self.fields['max_participants'].widget.attrs.update({
            'min': '1',
            'data-capacity-input': '1',
        })

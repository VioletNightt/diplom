from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User


class UserRegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['email', 'full_name', 'phone', 'school_class']
        labels = {
            'email': 'Email',
            'full_name': 'ФИО',
            'phone': 'Телефон',
            'school_class': 'Класс',
        }


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label='Email')

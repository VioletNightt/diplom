from django.contrib.auth import authenticate
from rest_framework import serializers

from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['id', 'email', 'password', 'full_name', 'phone', 'school_class']
        read_only_fields = ['id']

    def create(self, validated_data):
        return User.objects.create_user(role=User.Role.USER, **validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs['email'], password=attrs['password'])
        if not user:
            raise serializers.ValidationError('Неверный email или пароль.')
        if not user.is_active:
            raise serializers.ValidationError('Аккаунт заблокирован.')
        attrs['user'] = user
        return attrs


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'phone', 'role', 'school_class']
        read_only_fields = ['id', 'email', 'role']

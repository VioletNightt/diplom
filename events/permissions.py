from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin_role)


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return bool(request.user and request.user.is_authenticated and request.user.is_admin_role)


class IsAdminOrTeacherOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_admin_role:
            return True
        teacher_profile = getattr(request.user, 'teacher_profile', None)
        return bool(teacher_profile and getattr(obj, 'teacher_id', None) == teacher_profile.id)

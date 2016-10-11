from rest_framework import permissions


class IsOwnerOfProject(permissions.BasePermission):
    def has_object_permission(self, request, view, project):
        return project.owner == request.user if request.user else False


class IsSuperPowerfulUser(permissions.BasePermission):
    def has_object_permission(self, request, view, project):
        return request.user and request.user.is_super_powerful


class IsOwnerOfOrder(permissions.BasePermission):
    def has_object_permission(self, request, view, order):
        return order.project.owner == request.user if request.user else False

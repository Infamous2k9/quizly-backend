from rest_framework.permissions import BasePermission


class IsQuizOwner(BasePermission):
    """Allow access to a quiz only for the user who created it."""

    def has_object_permission(self, request, view, obj):
        """Return True if the requesting user owns the quiz."""
        return obj.user == request.user

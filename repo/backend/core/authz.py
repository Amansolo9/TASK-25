from rest_framework.response import Response

from access.services import user_has_permission


def require_permission(user, permission_code):
    if user_has_permission(user, permission_code):
        return None
    return Response({"detail": f"Missing permission: {permission_code}"}, status=403)

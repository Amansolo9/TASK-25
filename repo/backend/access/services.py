from access.models import BaseRole, RolePermission


def user_role_codes(user):
    if not user.is_authenticated:
        return set()
    return set(
        RolePermission.objects.filter(role__userrole__user=user)
        .values_list("role__code", flat=True)
        .distinct()
    )


def is_platform_admin(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return BaseRole.PLATFORM_ADMIN in user_role_codes(user)


def user_has_permission(user, permission_code):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True

    return RolePermission.objects.filter(
        role__userrole__user=user,
        permission__code=permission_code,
    ).exists()

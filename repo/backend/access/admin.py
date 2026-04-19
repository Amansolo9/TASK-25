from django.contrib import admin

from access.models import Permission, Role, RolePermission

admin.site.register(Permission)
admin.site.register(Role)
admin.site.register(RolePermission)

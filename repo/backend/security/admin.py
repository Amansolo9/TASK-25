from django.contrib import admin

from security.models import ApiClientKey, ReplayNonce, UnmaskAccessSession

admin.site.register(ApiClientKey)
admin.site.register(ReplayNonce)
admin.site.register(UnmaskAccessSession)

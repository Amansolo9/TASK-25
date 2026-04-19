from django.contrib import admin

from core.models import IdempotencyRecord

admin.site.register(IdempotencyRecord)

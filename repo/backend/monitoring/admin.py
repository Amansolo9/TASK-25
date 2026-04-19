from django.contrib import admin

from monitoring.models import AlertThreshold, AnomalyAlert

admin.site.register(AnomalyAlert)
admin.site.register(AlertThreshold)

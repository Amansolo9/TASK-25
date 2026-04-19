from django.contrib import admin

from warehouse.models import Location, PartnerRecord, Warehouse, Zone

admin.site.register(Warehouse)
admin.site.register(Zone)
admin.site.register(Location)
admin.site.register(PartnerRecord)

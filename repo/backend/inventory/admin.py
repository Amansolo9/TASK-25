from django.contrib import admin

from inventory.models import (
    CorrectiveAction,
    InventoryCountLine,
    InventoryPlan,
    InventoryTask,
    VarianceClosure,
)

admin.site.register(InventoryPlan)
admin.site.register(InventoryTask)
admin.site.register(InventoryCountLine)
admin.site.register(CorrectiveAction)
admin.site.register(VarianceClosure)

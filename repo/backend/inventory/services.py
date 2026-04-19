from django.db import transaction

from inventory.models import InventoryCountLine, VarianceClosure


def update_line_variance(line):
    line.calculate_variance()
    line.save(
        update_fields=[
            "variance_quantity",
            "variance_percent",
            "variance_type",
            "requires_review",
        ]
    )


@transaction.atomic
def close_variance_line(line, reviewer, review_notes=""):
    if line.requires_review:
        if not hasattr(line, "corrective_action"):
            raise ValueError("Corrective action is required before closure.")

        corrective = line.corrective_action
        if not corrective.accountability_acknowledged:
            raise ValueError("Accountability acknowledgment is required.")
        if corrective.approved_by is None:
            raise ValueError("Corrective action approval is required.")

    line.closed = True
    line.save(update_fields=["closed"])

    closure, _ = VarianceClosure.objects.update_or_create(
        line=line,
        defaults={"reviewer": reviewer, "review_notes": review_notes},
    )
    return closure

from django.db import migrations, models


def add_constraints_if_missing(apps, schema_editor):
    ComparisonItem = apps.get_model("accounts", "ComparisonItem")
    FavoriteItem = apps.get_model("accounts", "FavoriteItem")

    comparison_constraint = models.UniqueConstraint(
        fields=("user", "kind", "reference_id"),
        name="uniq_user_comparison",
    )
    favorite_constraint = models.UniqueConstraint(
        fields=("user", "kind", "reference_id"),
        name="uniq_user_favorite",
    )

    for model, constraint in (
        (ComparisonItem, comparison_constraint),
        (FavoriteItem, favorite_constraint),
    ):
        try:
            schema_editor.add_constraint(model, constraint)
        except Exception:
            pass


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_alter_user_groups_alter_user_is_active"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    add_constraints_if_missing,
                    reverse_code=migrations.RunPython.noop,
                )
            ],
            state_operations=[
                migrations.AddConstraint(
                    model_name="comparisonitem",
                    constraint=models.UniqueConstraint(
                        fields=("user", "kind", "reference_id"),
                        name="uniq_user_comparison",
                    ),
                ),
                migrations.AddConstraint(
                    model_name="favoriteitem",
                    constraint=models.UniqueConstraint(
                        fields=("user", "kind", "reference_id"),
                        name="uniq_user_favorite",
                    ),
                ),
            ],
        )
    ]

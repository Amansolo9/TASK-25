from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("audit", "0001_initial"),
    ]

    operations = [
        migrations.RenameIndex(
            model_name="auditevent",
            new_name="audit_audit_organiz_17c31e_idx",
            old_name="audit_audit_organiz_6cc87f_idx",
        ),
        migrations.RenameIndex(
            model_name="auditevent",
            new_name="audit_audit_created_7710b7_idx",
            old_name="audit_audit_created_50e7f9_idx",
        ),
    ]

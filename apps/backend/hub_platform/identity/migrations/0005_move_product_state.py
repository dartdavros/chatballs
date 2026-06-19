from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0004_employeeprofile_phone"),
        ("products", "0001_move_product_state"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[migrations.DeleteModel(name="Product")],
        )
    ]

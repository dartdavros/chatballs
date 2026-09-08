from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('identity', '0030_instance_turn'),
    ]

    operations = [
        migrations.AddField(
            model_name='humanuser',
            name='totp_last_counter',
            field=models.BigIntegerField(default=0),
        ),
    ]

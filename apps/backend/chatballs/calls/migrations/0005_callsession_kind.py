from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calls', '0004_alter_callinvite_organization_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='callsession',
            name='kind',
            field=models.CharField(
                choices=[('AUDIO', 'Аудиозвонок'), ('VIDEO', 'Видеозвонок')],
                db_index=True,
                default='AUDIO',
                max_length=8,
            ),
        ),
    ]

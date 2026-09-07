# Вид сообщения «файл» (`MessageKind.FILE`) появился в модели без миграции —
# состояние догоняем здесь. Только choices: на схему БД не влияет.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('conversations', '0018_contact_merge'),
    ]

    operations = [
        migrations.AlterField(
            model_name='message',
            name='kind',
            field=models.CharField(blank=True, choices=[('', 'Текст'), ('contact_request', 'Запрос контакта'), ('contact', 'Контакт'), ('voice', 'Голосовое сообщение'), ('file', 'Файл')], default='', max_length=32),
        ),
    ]

"""Свежесть диалога — отдельным полем, порядок инбокса — по индексу.

Раньше список сортировался по агрегату max(messages.created_at): такой ключ не
ложится ни в индекс, ни в курсор окна, поэтому каждый запрос инбокса собирал
GROUP BY по всей ленте сообщений. Поле заполняется здесь и дальше держится
сигналом (chatballs.conversations.signals).
"""

import django.utils.timezone
from django.conf import settings
from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations, models

CONTACT_TRGM_INDEXES = """
CREATE INDEX IF NOT EXISTS contact_name_trgm
    ON conversations_contact USING gin ((UPPER(name)) gin_trgm_ops);
CREATE INDEX IF NOT EXISTS contact_phone_trgm
    ON conversations_contact USING gin ((UPPER(phone)) gin_trgm_ops);
"""

DROP_CONTACT_TRGM_INDEXES = """
DROP INDEX IF EXISTS contact_name_trgm;
DROP INDEX IF EXISTS contact_phone_trgm;
"""

BACKFILL = """
UPDATE conversations_conversation AS c
SET last_message_at = COALESCE(
    (SELECT MAX(m.created_at) FROM conversations_message AS m WHERE m.conversation_id = c.id),
    c.last_activity_at
)
"""


class Migration(migrations.Migration):

    dependencies = [
        ('channels', '0008_remove_channel_allow_checkout_actions_and_more'),
        ('conversations', '0019_alter_message_kind'),
        ('identity', '0032_remove_organization_tax_regime_and_more'),
        ('integrations', '0007_integration_feature_flags'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Поиск по контактам идёт подстрокой — без триграмм это перебор таблицы.
        TrigramExtension(),
        migrations.AddField(
            model_name='conversation',
            name='last_message_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.RunSQL(sql=BACKFILL, reverse_sql=migrations.RunSQL.noop),
        # Функциональный индекс с opclass заводится сырым SQL: Django 5.2
        # рендерит его как «(UPPER(name) gin_trgm_ops)» — без скобок вокруг
        # самого выражения, и Postgres такой синтаксис отвергает.
        migrations.RunSQL(sql=CONTACT_TRGM_INDEXES, reverse_sql=DROP_CONTACT_TRGM_INDEXES),
        migrations.AddIndex(
            model_name='conversation',
            index=models.Index(
                fields=['organization', '-last_message_at', '-id'], name='conv_inbox_order'
            ),
        ),
        migrations.AddIndex(
            model_name='conversation',
            index=models.Index(fields=['contact', '-last_activity_at'], name='conv_contact_recent'),
        ),
        migrations.AddIndex(
            model_name='message',
            index=models.Index(
                fields=['conversation', 'created_at', 'id'], name='conv_message_window'
            ),
        ),
    ]

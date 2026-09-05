# Платформенные строки аудита и outbox (organization_id IS NULL: вход/выход)
# невидимы runtime-ролям под RLS, поэтому Django-каскад SET_NULL до них не
# доходит и удаление пользователя (снятие демо) падало на FK. Переносим
# SET NULL на уровень БД для этих двух ссылок — семантика та же, что в моделях.
from django.db import migrations

FORWARD = """
ALTER TABLE identity_auditevent
    DROP CONSTRAINT identity_auditevent_actor_id_b3fc4d10_fk_identity_humanuser_id,
    ADD CONSTRAINT identity_auditevent_actor_id_b3fc4d10_fk_identity_humanuser_id
        FOREIGN KEY (actor_id) REFERENCES identity_humanuser (id)
        ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE events_outboxevent
    DROP CONSTRAINT events_outboxevent_actor_user_id_f9bdf9a9_fk_identity_,
    ADD CONSTRAINT events_outboxevent_actor_user_id_f9bdf9a9_fk_identity_
        FOREIGN KEY (actor_user_id) REFERENCES identity_humanuser (id)
        ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED;
"""

BACKWARD = """
ALTER TABLE identity_auditevent
    DROP CONSTRAINT identity_auditevent_actor_id_b3fc4d10_fk_identity_humanuser_id,
    ADD CONSTRAINT identity_auditevent_actor_id_b3fc4d10_fk_identity_humanuser_id
        FOREIGN KEY (actor_id) REFERENCES identity_humanuser (id)
        DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE events_outboxevent
    DROP CONSTRAINT events_outboxevent_actor_user_id_f9bdf9a9_fk_identity_,
    ADD CONSTRAINT events_outboxevent_actor_user_id_f9bdf9a9_fk_identity_
        FOREIGN KEY (actor_user_id) REFERENCES identity_humanuser (id)
        DEFERRABLE INITIALLY DEFERRED;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0023_user_delete_grants"),
        ("identity", "0024_employeegroup_color"),
        ("events", "0001_initial"),
    ]

    operations = [migrations.RunSQL(FORWARD, BACKWARD)]

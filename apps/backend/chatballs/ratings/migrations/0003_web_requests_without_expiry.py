"""WEB credentials have no time limit, including previously expired requests.

Keep every existing row untouched. Legacy expires_at values remain historical
data, ignored only for the immutable WEB transport of the completion fact.
Downgrading would revoke accepted credentials, so this migration is irreversible.
"""

from django.db import migrations, models


GUARDS = """
CREATE OR REPLACE FUNCTION chatballs.guard_rating_request() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE completion conversations_conversationevent%%ROWTYPE;
BEGIN
    IF NEW.sent_at IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM conversations_conversationevent
        WHERE id = NEW.completion_id AND organization_id = NEW.organization_id AND transport = 'WEB'
    ) AND NEW.expires_at IS DISTINCT FROM NEW.sent_at + interval '7 days'
    THEN RAISE EXCEPTION 'rating expiry must be seven days after sending'; END IF;
    IF TG_OP = 'UPDATE' THEN
        IF (to_jsonb(NEW) - ARRAY['sent_at', 'cancelled_at', 'credential_hash', 'expires_at'])
            IS DISTINCT FROM
           (to_jsonb(OLD) - ARRAY['sent_at', 'cancelled_at', 'credential_hash', 'expires_at'])
        THEN RAISE EXCEPTION 'rating snapshot is immutable'; END IF;
        IF OLD.sent_at IS NOT NULL AND
           ROW(NEW.sent_at, NEW.credential_hash, NEW.expires_at) IS DISTINCT FROM
           ROW(OLD.sent_at, OLD.credential_hash, OLD.expires_at)
        THEN RAISE EXCEPTION 'rating credential is immutable'; END IF;
        IF OLD.cancelled_at IS NOT NULL AND NEW.cancelled_at IS DISTINCT FROM OLD.cancelled_at
        THEN RAISE EXCEPTION 'rating cancellation is final'; END IF;
        IF OLD.cancelled_at IS NOT NULL AND NEW.sent_at IS DISTINCT FROM OLD.sent_at
        THEN RAISE EXCEPTION 'cancelled rating cannot be delivered'; END IF;
        RETURN NEW;
    END IF;
    PERFORM id FROM conversations_conversation
        WHERE id = NEW.conversation_id AND organization_id = NEW.organization_id FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'rating conversation unavailable'; END IF;
    SELECT * INTO completion FROM conversations_conversationevent
        WHERE id = NEW.completion_id AND organization_id = NEW.organization_id;
    IF NOT FOUND OR completion.event_type <> 'CLOSED'
        OR completion.conversation_id <> NEW.conversation_id
    THEN RAISE EXCEPTION 'rating completion mismatch'; END IF;
    IF NOT chatballs.valid_rating_scale(NEW.scale) OR length(btrim(NEW.text)) = 0
        OR length(NEW.text) > 4000 OR NEW.delay_seconds > 604800
    THEN RAISE EXCEPTION 'invalid rating snapshot'; END IF;
    NEW.due_at := completion.occurred_at + NEW.delay_seconds * interval '1 second';
    SELECT session.id INTO NEW.delivery_session_id
        FROM webchat_websession session JOIN conversations_conversation conversation
          ON conversation.id = NEW.conversation_id
        WHERE session.organization_id = NEW.organization_id
          AND session.connection_id = conversation.connection_id
          AND session.identity_id IN (SELECT id FROM conversations_connectionidentity
              WHERE contact_id = conversation.contact_id AND connection_id = conversation.connection_id)
          AND session.widget_id::text = conversation.transport_meta->>'webChatWidgetId'
        ORDER BY session.id LIMIT 1;
    SELECT COALESCE(jsonb_agg(user_id ORDER BY user_id), '[]'::jsonb)
        INTO NEW.responder_ids FROM (
            SELECT initiated_by_id AS user_id FROM conversations_conversationevent
            WHERE conversation_id = NEW.conversation_id AND organization_id = NEW.organization_id
              AND sequence < completion.sequence AND event_type = 'PUBLIC_REPLY'
              AND actor_kind = 'HUMAN' AND initiated_by_id IS NOT NULL
            UNION
            SELECT author_user_id FROM conversations_message
            WHERE conversation_id = NEW.conversation_id AND organization_id = NEW.organization_id
              AND created_at <= completion.occurred_at AND author_type = 'OPERATOR'
              AND system_event = '' AND kind IN ('', 'file', 'voice', 'contact_request')
              AND author_user_id IS NOT NULL
        ) responders;
    RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION chatballs.guard_customer_rating() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE target ratings_ratingrequest%%ROWTYPE;
BEGIN
    IF TG_OP = 'UPDATE' THEN RAISE EXCEPTION 'customer rating is immutable'; END IF;
    SELECT * INTO target FROM ratings_ratingrequest
        WHERE id = NEW.request_id AND organization_id = NEW.organization_id FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'rating request unavailable'; END IF;
    IF target.sent_at IS NULL OR target.cancelled_at IS NOT NULL OR (
        (target.expires_at IS NULL OR target.expires_at <= clock_timestamp()) AND NOT EXISTS (
            SELECT 1 FROM conversations_conversationevent
            WHERE id = target.completion_id AND organization_id = target.organization_id AND transport = 'WEB'
        )
    ) THEN RAISE EXCEPTION 'rating request is inactive'; END IF;
    IF NOT EXISTS (SELECT 1 FROM jsonb_array_elements(target.scale) choice
                   WHERE choice->>'value' = NEW.value)
    THEN RAISE EXCEPTION 'rating value is outside the snapshot'; END IF;
    IF length(NEW.comment) > 2000 THEN RAISE EXCEPTION 'rating comment is too long'; END IF;
    NEW.received_at := clock_timestamp();
    RETURN NEW;
END $$;

CREATE OR REPLACE VIEW chatballs.rating_request_directory WITH (security_barrier = true) AS
    SELECT id AS resource_id, organization_id, credential_hash AS lookup_key
    FROM ratings_ratingrequest request WHERE sent_at IS NOT NULL AND cancelled_at IS NULL
      AND (expires_at > clock_timestamp() OR EXISTS (
          SELECT 1 FROM conversations_conversationevent completion
          WHERE completion.id = request.completion_id
            AND completion.organization_id = request.organization_id AND completion.transport = 'WEB'
      ));
"""


def forward(apps, schema_editor):
    # Preserve function/view owners, grants, RLS and the existing trigger bindings.
    schema_editor.execute(GUARDS)


class Migration(migrations.Migration):
    dependencies = [("ratings", "0002_guards")]
    operations = [
        migrations.RemoveConstraint(model_name="ratingrequest", name="rating_credential_lifecycle"),
        migrations.AddConstraint(
            model_name="ratingrequest",
            constraint=models.CheckConstraint(
                condition=models.Q(sent_at__isnull=True, credential_hash__isnull=True, expires_at__isnull=True)
                | models.Q(sent_at__isnull=False, credential_hash__isnull=False),
                name="rating_credential_lifecycle",
            ),
        ),
        migrations.RunPython(forward),
    ]

"""Демо-контакты, связанные каналы, метки и шаблоны ответов."""

from chatballs.conversations.models import (
    ConnectionIdentity,
    Contact,
    ConversationLabel,
    ReplyTemplate,
)
from chatballs.identity.demo_seed import manifest
from chatballs.identity.demo_seed.loaders.common import backdate, moment, now
from chatballs.identity.demo_seed.refs import DemoRefs

AVATAR_URL = "/api/v1/demo-media/avatars/{name}"


def load(refs: DemoRefs) -> None:
    data = manifest.load("contacts", refs.language)
    organization = refs.organization
    current = now()

    for item in data["contacts"]:
        contact, created = Contact.objects.get_or_create(
            organization=organization,
            name=item["name"],
            defaults={
                "phone": item.get("phone", ""),
                "avatar_url": AVATAR_URL.format(name=item["avatar"]) if item.get("avatar") else "",
                "description": item.get("description", ""),
                "company": item.get("company", ""),
                "city": item.get("city", ""),
            },
        )
        if created:
            backdate(contact, moment(item, current, "created"))
        refs.contacts[item["key"]] = contact

    for item in data["connectionIdentities"]:
        _ensure_identity(refs, item)

    for item in data.get("labels", []):
        label, _ = ConversationLabel.objects.get_or_create(
            organization=organization, name=item["name"], defaults={"color": item.get("color", "")}
        )
        refs.labels[item["key"]] = label

    for item in data.get("replyTemplates", []):
        ReplyTemplate.objects.get_or_create(
            organization=organization, title=item["title"], defaults={"text": item["text"]}
        )

    # Объединение контактов (ADR-CHATBALLS-0006): демо показывает и историю слияний.
    for item in data.get("contactMerges", []):
        _merge_contacts(refs, item)


def _merge_contacts(refs: DemoRefs, item: dict) -> None:
    from chatballs.conversations.contacts_merge import merge_contacts
    from chatballs.conversations.models import ContactMerge

    target = refs.contacts[item["target"]]
    source = refs.contacts[item["source"]]
    if ContactMerge.objects.filter(target=target, source=source).exists():
        return
    merge_contacts(
        organization=refs.organization,
        target_id=target.id,
        source_id=source.id,
        reason=item["reason"],
        actor=refs.users.get(item.get("actor")),
    )


def _ensure_identity(refs: DemoRefs, item: dict) -> None:
    connection = refs.integrations[item["connection"]]
    contact = refs.contacts[item["contact"]]
    ConnectionIdentity.objects.get_or_create(
        connection=connection,
        external_user_id=item["externalUserId"],
        defaults={
            "organization": refs.organization,
            "contact": contact,
            "display_name": item.get("displayName", ""),
            "username": item.get("username", ""),
        },
    )

#!/usr/bin/env python3
"""Explicit, local-only CustoCRM demo data importer.

This file is mounted only by compose.dev.yaml and is intentionally outside the
backend image. It must never be copied into or executed by a production setup.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import timedelta
from pathlib import Path


SEED_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = SEED_DIR / "manifest.json"


def require_local_environment() -> None:
    if os.environ.get("CUS_ENV") != "local" or os.environ.get("CUSTOCRM_LOCAL_SEED") != "1":
        raise SystemExit("Local seed is available only through compose.dev.yaml with CUS_ENV=local.")


def load_manifest() -> dict:
    with MANIFEST_PATH.open(encoding="utf-8") as stream:
        manifest = json.load(stream)
    if manifest.get("schemaVersion") != 1:
        raise SystemExit("Unsupported local seed manifest version.")
    return manifest


def run() -> None:
    require_local_environment()
    sys.path.insert(0, "/app/apps/backend")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hub_backend.settings")

    import django

    django.setup()

    from django.db import transaction
    from django.utils import timezone

    from hub_platform.ai.knowledge_categories import ensure_uncategorized_category
    from hub_platform.ai.models import AIAgent, AIAgentStatus, LlmInvocation
    from hub_platform.channels.models import Channel
    from hub_platform.conversations.models import (
        ConnectionIdentity,
        Contact,
        Conversation,
        ControlMode,
        ExpectedResponder,
        LifecycleState,
        Message,
        MessageAuthor,
    )
    from hub_platform.identity.access_defaults import ensure_system_assignment
    from hub_platform.identity.models import Department, EmployeeRole, HumanUser, Organization, OrganizationMembership
    from hub_platform.integrations.models import Integration, IntegrationKind
    from hub_platform.orders.models import FulfillmentStatus, Order, PaymentStatus
    from hub_platform.products.models import Product, ProductDepartment
    from hub_platform.subscriptions.default_subscription import ensure_default_subscription

    manifest = load_manifest()
    now = timezone.now()

    with transaction.atomic():
        org_data = manifest["organization"]
        organization, _ = Organization.objects.get_or_create(
            slug=org_data["slug"],
            defaults={
                "name": org_data["name"],
                "timezone": org_data["timezone"],
                "currency": org_data["currency"],
            },
        )
        ensure_uncategorized_category(organization)
        ensure_default_subscription(organization)

        departments = {}
        for item in manifest["departments"]:
            department, _ = Department.objects.get_or_create(
                organization=organization, code=item["code"], defaults={"name": item["name"]}
            )
            departments[item["code"]] = department

        accounts = manifest["accounts"]
        owner_data = accounts["owner"]
        owner, owner_created = HumanUser.objects.get_or_create(
            email=HumanUser.objects.normalize_email(owner_data["email"]),
            defaults={"full_name": owner_data["fullName"], "is_staff": True, "is_superuser": True},
        )
        if owner_created:
            owner.set_password(owner_data["password"])
            owner.save(update_fields=["password"])
        owner_membership, _ = OrganizationMembership.objects.get_or_create(
            user=owner,
            organization=organization,
            defaults={"role": EmployeeRole.OWNER, "position_title": owner_data["positionTitle"]},
        )
        if owner_membership.role != EmployeeRole.OWNER:
            raise SystemExit(f"{owner.email} is not the owner of local organization {organization.slug}.")

        operator_data = accounts["operator"]
        operator, operator_created = HumanUser.objects.get_or_create(
            email=HumanUser.objects.normalize_email(operator_data["email"]),
            defaults={"full_name": operator_data["fullName"]},
        )
        if operator_created:
            operator.set_password(operator_data["password"])
            operator.save(update_fields=["password"])
        operator_membership, _ = OrganizationMembership.objects.get_or_create(
            user=operator,
            organization=organization,
            defaults={
                "role": EmployeeRole.EMPLOYEE,
                "position_title": operator_data["positionTitle"],
                "phone": operator_data["phone"],
                "primary_department": departments["sales"],
            },
        )
        ensure_system_assignment(
            employee=operator_membership,
            assigned_by=owner_membership,
            department=departments["sales"],
            profile_name="Sales operator",
        )

        products = {}
        for item in manifest["products"]:
            product, _ = Product.objects.get_or_create(
                organization=organization, code=item["code"], defaults={"name": item["name"]}
            )
            products[item["code"]] = product
            for department_code in item["departments"]:
                ProductDepartment.objects.get_or_create(product=product, department=departments[department_code])

        channels = {}
        for item in manifest["channels"]:
            channel, _ = Channel.objects.get_or_create(
                organization=organization,
                code=item["code"],
                defaults={
                    "name": item["name"],
                    "department": departments.get(item["department"]),
                    "product": products.get(item["product"]),
                    "is_active": item.get("isActive", True),
                    **item["policy"],
                },
            )
            channels[item["code"]] = channel
            agent_data = item.get("agent")
            if agent_data:
                AIAgent.objects.get_or_create(
                    channel=channel,
                    defaults={
                        "name": agent_data["name"],
                        "model": agent_data["model"],
                        "status": AIAgentStatus.ACTIVE,
                    },
                )

        integrations = {}
        for item in manifest["integrations"]:
            integration, _ = Integration.objects.get_or_create(
                organization=organization,
                provider=item["provider"],
                name=item["name"],
                defaults={
                    "kind": IntegrationKind.MESSENGER,
                    "channel": channels[item["channel"]],
                    "status": item["status"],
                },
            )
            integrations[item["key"]] = integration

        contacts = {}
        for item in manifest["contacts"]:
            connection = integrations[item["connection"]]
            identity = ConnectionIdentity.objects.filter(
                connection=connection, external_user_id=item["externalUserId"]
            ).select_related("contact").first()
            if identity is None:
                contact = Contact.objects.create(organization=organization, name=item["name"], phone=item["phone"])
                ConnectionIdentity.objects.create(
                    organization=organization,
                    contact=contact,
                    connection=connection,
                    external_user_id=item["externalUserId"],
                    display_name=item["name"],
                )
            else:
                contact = identity.contact
            contacts[item["key"]] = contact

        conversations = {}
        for item in manifest["conversations"]:
            conversation, _ = Conversation.objects.get_or_create(
                organization=organization,
                channel=channels[item["channel"]],
                external_chat_id=item["externalChatId"],
                defaults={
                    "connection": integrations[item["connection"]],
                    "contact": contacts[item["contact"]],
                    "lifecycle": LifecycleState.OPEN,
                    "control_mode": item["controlMode"],
                    "expected_responder": item["expectedResponder"],
                    "assigned_operator": operator if item["controlMode"] == ControlMode.HUMAN else None,
                    "transport_meta": {"localSeedKey": item["key"]},
                },
            )
            Conversation.objects.filter(pk=conversation.pk).update(
                last_activity_at=now - timedelta(minutes=item["lastActivityMinutesAgo"])
            )
            conversation.refresh_from_db()
            conversations[item["key"]] = conversation
            for message in item["messages"]:
                Message.objects.get_or_create(
                    conversation=conversation,
                    external_id=message["externalId"],
                    defaults={
                        "author_type": message["author"],
                        "author_user": operator if message["author"] == MessageAuthor.OPERATOR else None,
                        "text": message["text"],
                    },
                )

        for item in manifest["orders"]:
            payment_status = item["paymentStatus"]
            Order.objects.get_or_create(
                organization=organization,
                source="local-seed",
                external_id=item["externalId"],
                defaults={
                    "product": products[item["product"]],
                    "contact": contacts[item["contact"]],
                    "conversation": conversations[item["conversation"]],
                    "channel": conversations[item["conversation"]].channel,
                    "payment_status": payment_status,
                    "fulfillment_status": item["fulfillmentStatus"],
                    "amount_minor": item["amountMinor"],
                    "paid_at": now if payment_status == PaymentStatus.PAID else None,
                },
            )

        for item in manifest["aiInvocations"]:
            channel = channels[item["channel"]]
            LlmInvocation.objects.get_or_create(
                channel=channel,
                purpose=item["purpose"],
                operation="chat",
                model=item["model"],
                defaults={
                    "product": products[item["product"]],
                    "prompt_tokens": item["promptTokens"],
                    "completion_tokens": item["completionTokens"],
                    "total_tokens": item["promptTokens"] + item["completionTokens"],
                    "cost_micros": item["costMicros"],
                },
            )

    print(json.dumps({
        "organization": organization.slug,
        "organizationPublicId": str(organization.public_id),
        "owner": owner.email,
        "operator": operator.email,
        "channels": Channel.objects.filter(organization=organization).count(),
        "integrations": Integration.objects.filter(organization=organization).count(),
        "conversations": Conversation.objects.filter(organization=organization).count(),
        "orders": Order.objects.filter(organization=organization).count(),
        "idempotent": True,
    }, ensure_ascii=False))


if __name__ == "__main__":
    run()

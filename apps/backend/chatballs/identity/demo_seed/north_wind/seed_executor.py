"""Provision a native external-agent binding behind the shared support widget."""

from secrets import token_urlsafe
from uuid import uuid4

from django.utils import timezone

from chatballs.ai.external_agents.adapter import PROFILE, check_capabilities
from chatballs.ai.external_agents.auth import key_hash
from chatballs.ai.external_agents.config_models import ExternalAgentBinding, ExternalAgentConnection
from chatballs.ai.external_agents.grant_definitions import definitions
from chatballs.ai.skill_templates.order_basis import order_basis
from chatballs.ai.skills_models import AgentSkill, Skill
from chatballs.ai.skills_validation import configuration
from chatballs.identity.demo_seed import manifest
from chatballs.identity.demo_seed.north_wind.executor_scope import (
    EXECUTOR_URL,
    MARKER,
    inbound_key,
    outbound_key,
)
from chatballs.integrations.models import Integration, ServiceConnectionSettings
from chatballs.integrations.service_connections.binding import dump_credentials


def load_executor(refs):
    if not refs.recorder or not refs.recorder.dataset.shop_state.get("localTools"):
        return
    dataset = refs.recorder.dataset
    copy = manifest.load("north_wind", refs.language)["externalExecutor"]
    connection = _connection(dataset, copy["service"])
    agent = refs.agents["support"]
    agent.execution_mode = "external"
    agent.save(update_fields=["execution_mode"])
    binding = _bind_executor(refs, connection, agent)
    dataset.shop_state["externalExecutor"] = {
        "connectionId": connection.pk, "agentId": agent.pk, "widgetConnectionId": refs.integrations["web_help"].pk,
        "templateIds": binding.template_ids,
    }
    dataset.save(update_fields=["shop_state"])


def _connection(dataset, name):
    integration = Integration.objects.create(
        organization_id=dataset.organization_id, name=name, kind="SERVICE", provider="ADAPTER",
        config={MARKER: str(dataset.generation)},
    )
    connection = ExternalAgentConnection.objects.create(
        integration=integration, deduplication_key=token_urlsafe(48),
    )
    token = outbound_key(dataset, connection.pk)
    capabilities = check_capabilities(EXECUTOR_URL, token)
    ServiceConnectionSettings.objects.create(
        integration=integration, adapter_key=PROFILE, adapter_version=1, auth_method="bearer",
        settings={"base_url": EXECUTOR_URL}, credentials=dump_credentials({"token": token}),
    )
    connection.capabilities, connection.checked_at = capabilities, timezone.now()
    connection.inbound_key_hash = key_hash(inbound_key(dataset, connection.pk))
    connection.save(update_fields=["capabilities", "checked_at", "inbound_key_hash"])
    integration.status, integration.last_checked_at = "OK", connection.checked_at
    integration.save(update_fields=["status", "last_checked_at"])
    return connection


def _bind_executor(refs, connection, agent):
    source = order_basis(language=refs.language)
    source["name"] += f" · {agent.channel.name}"
    for template in source["templates"]:
        template["id"] = str(uuid4())
    skill = Skill.objects.create(organization=refs.organization, **configuration(source))
    AgentSkill.objects.create(organization=refs.organization, skill=skill, agent=agent)
    binding = ExternalAgentBinding.objects.create(
        connection=connection, agent=agent, external_agent_id="north-wind",
        policy_accepted=True, template_ids=[template["id"] for template in skill.templates],
    )
    binding.accepted_definitions = definitions(binding)
    binding.save(update_fields=["accepted_definitions"])
    return binding

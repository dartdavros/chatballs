"""Authority for the executor provisioned by this local demo generation."""

from django.core import signing
from django.core.exceptions import ObjectDoesNotExist
from django.utils.crypto import salted_hmac

from chatballs.identity.demo_models import DemoDataset, DemoDatasetStatus
from chatballs.identity.demo_seed.north_wind.local_access import local_demo_enabled

EXECUTOR_ORIGIN = "https://north-wind-external-tls:8443"
EXECUTOR_URL = EXECUTOR_ORIGIN + "/executor"
EXECUTOR_CA = "/run/north-wind-trust/root.crt"
MARKER = "northWindExecutor"
RESET_EVENT = "demo.external_executor_reset"
_OUTBOUND_SALT = "north-wind-executor-outbound"
_INBOUND_SALT = "north-wind-executor-inbound"


def is_local_executor(connection):
    return bool(connection.integration.config.get(MARKER))


def active_executor(organization_id, connection, *, agent_id=None):
    if not local_demo_enabled() or not is_local_executor(connection):
        return None
    generation = connection.integration.config[MARKER]
    service = getattr(connection.integration, "service_settings", None)
    if (not connection.enabled or not connection.integration.is_active
            or service is None or service.settings.get("base_url") != EXECUTOR_URL):
        return None
    dataset = DemoDataset.objects.filter(
        organization_id=organization_id, generation=generation, status=DemoDatasetStatus.INSTALLED,
    ).first()
    binding = dataset.shop_state.get("externalExecutor", {}) if dataset else {}
    if binding.get("connectionId") != connection.pk or (agent_id is not None and binding.get("agentId") != agent_id):
        return None
    return dataset


def execution_enabled(organization, connection, *, agent_id=None):
    if is_local_executor(connection):
        return active_executor(organization.pk, connection, agent_id=agent_id) is not None
    return organization.external_execution_enabled


def allows_conversation(organization, connection, agent, conversation):
    if not is_local_executor(connection):
        return True
    dataset = active_executor(organization.pk, connection, agent_id=agent.pk)
    if dataset is None:
        return False
    return _matches_conversation(dataset, conversation)


def _matches_conversation(dataset, conversation):
    binding = dataset.shop_state["externalExecutor"]
    return conversation.is_test or (
        conversation.pk == binding.get("conversationId") and conversation.connection_id == binding.get("widgetConnectionId")
    )


def uses_external_execution(agent, *, conversation=None):
    if agent.execution_mode != "external":
        return False
    if conversation is None:
        return True
    try:
        service = agent.external_binding.connection
    except ObjectDoesNotExist:
        return True
    dataset = active_executor(conversation.organization_id, service, agent_id=agent.pk)
    if dataset is None or conversation.connection is None:
        return True
    # Only generation-owned demo integrations can share the builtin support path.
    config = conversation.connection.config
    if not config.get("demoSeed") or config.get("demoGeneration") != str(dataset.generation):
        return True
    return _matches_conversation(dataset, conversation)


def outbound_key(dataset, connection_id):
    return scope_key(dataset.organization_id, dataset.generation, connection_id)


def scope_key(organization_id, generation, connection_id):
    return signing.dumps([organization_id, str(generation), connection_id], salt=_OUTBOUND_SALT)


def inbound_key(dataset, connection_id):
    value = f"{dataset.organization_id}:{dataset.generation}:{connection_id}"
    return salted_hmac(_INBOUND_SALT, value, algorithm="sha256").hexdigest()


def read_executor_key(authorization):
    scheme, _, token = (authorization or "").partition(" ")
    if not local_demo_enabled() or scheme != "Bearer" or not 0 < len(token) <= 512:
        return None
    try:
        return signing.loads(token, salt=_OUTBOUND_SALT)
    except signing.BadSignature:
        return None

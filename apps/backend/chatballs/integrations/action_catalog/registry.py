"""One native registry for editor metadata, runtime and API coverage."""

from dataclasses import dataclass

from chatballs.integrations.adapters.schema import TypeSpec, validate_spec


@dataclass(frozen=True)
class ActionSchema:
    key: str
    title_key: str
    input: TypeSpec
    output: TypeSpec
    permission_scope: str
    authority: str = "tenant"


_ACTIONS: dict[str, ActionSchema] = {}
_EXECUTABLE = {}
_loaded = False


def register_action_schema(schema: ActionSchema):
    if schema.key in _ACTIONS:
        raise ValueError(f"Duplicate action: {schema.key}")
    validate_spec(schema.input)
    validate_spec(schema.output)
    _ACTIONS[schema.key] = schema


def action_schemas(*, authority="tenant"):
    load_actions()
    return tuple(a for a in _ACTIONS.values() if authority is None or a.authority == authority)


def register_action(action):
    from chatballs.integrations.adapters.contracts import READ_EFFECTS, RetryStrategy

    if action.authority not in {"tenant", "personal", "instance", "platform", "bootstrap"}:
        raise ValueError(f"Invalid authority: {action.key}")
    if action.key in _EXECUTABLE or not callable(action.execute):
        raise ValueError(f"Invalid executable action: {action.key}")
    if action.execution not in {"local", "io"} or action.contract_version < 1:
        raise ValueError(f"Invalid execution contract: {action.key}")
    if action.execution == "io" and action.operation.effect not in READ_EFFECTS and action.operation.retry != RetryStrategy.NONE:
        raise ValueError(f"I/O action needs an explicit recovery implementation: {action.key}")
    register_action_schema(ActionSchema(action.key, action.operation.title_key,
        action.operation.input, action.operation.output, action.scope, action.authority))
    _EXECUTABLE[action.key] = action
    return action


def load_actions():
    global _loaded
    if not _loaded:
        # Imports are intentionally explicit. No package scanning or arbitrary
        # module names are accepted from a scenario definition.
        from chatballs.integrations.action_catalog import (  # noqa: F401
            agent_policies,
            agents,
            assistance,
            availability,
            calls,
            comments,
            connections,
            contacts,
            conversation_management,
            conversation_metadata,
            conversation_reads,
            conversations,
            email,
            employees,
            entity_links,
            file_reads,
            groups,
            inbox,
            instance,
            knowledge,
            knowledge_categories,
            knowledge_files,
            knowledge_links,
            labels,
            messages,
            notifications,
            organizations,
            participants,
            platform,
            portal_articles,
            portal_categories,
            portal_files,
            portal_public,
            portals,
            profile,
            quality,
            ratings,
            reports,
            rules,
            run_management,
            scenario_metadata,
            scenarios,
            service_connections,
            settings,
            setup,
            skills,
            storage,
            synchronization,
            template_taxonomies,
            template_tools,
            templates,
            transcription,
            transfers,
            updates,
            webchat,
            widget_calls,
        )

        _loaded = True


def native_actions(*, authority="tenant"):
    load_actions()
    return tuple(a for a in _EXECUTABLE.values() if authority is None or a.authority == authority)


def native_action(key, *, authority="tenant"):
    load_actions()
    action = _EXECUTABLE.get(key)
    return action if action and (authority is None or action.authority == authority) else None


# Metadata needed by installed presets; no link is created when editing.
register_action_schema(ActionSchema(
    key="entity_link.create", title_key="scenarios.link_action", permission_scope="conversation",
    input=TypeSpec("object", properties=(
        ("connection", TypeSpec("integer", required=True, title_key="scenarios.connection")),
        ("entity", TypeSpec("string", required=True, title_key="scenarios.entity")),
        ("external_id", TypeSpec("string", required=True, title_key="scenarios.external_id")),
    )),
    output=TypeSpec("object", properties=(("id", TypeSpec("string")),)),
))

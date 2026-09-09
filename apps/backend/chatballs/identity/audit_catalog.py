"""Словарь журнала аудита: человеческие названия действий и их разделы.

Журнал был нечитаем: из 67 действий, которые пишет код, подписи имели 24, а
остальные схлопывались в одну строку «Системное действие» — по такому журналу
нельзя понять, что произошло. Здесь подписи на всё, что пишется, плюс два
правила, чтобы это не повторилось:

* раздел (`category`) выводится из префикса действия, а не из словаря, — новое
  действие попадает в свой раздел само и участвует в фильтрах;
* у действия без подписи `label` пустой, и интерфейс показывает сырой код
  моноширинным. Не «Системное действие» на всё подряд: код видно и понятно,
  какую подпись добавить сюда.
"""

from __future__ import annotations

from chatballs.i18n import t

# Разделы журнала: по ним фильтр и группировка. Ключ — префикс кода действия
# до первой точки.
AUDIT_CATEGORY_LABELS: dict[str, str] = {
    "identity": "audit.category_identity",
    "access_assignment": "audit.category_access_assignment",
    "administration": "audit.category_administration",
    "organization": "audit.category_organization",
    "integrations": "audit.category_integrations",
    "channels": "audit.category_channels",
    "ai": "audit.category_ai",
    "conversations": "audit.category_conversations",
    "conversation": "audit.category_conversation",
    "contacts": "audit.category_contacts",
    "calls": "audit.category_calls",
    "support_portal": "audit.category_support_portal",
    "demo": "audit.category_demo",
}

AUDIT_CATEGORY_ORDER = (
    "identity",
    "administration",
    "organization",
    "integrations",
    "channels",
    "ai",
    "conversations",
    "contacts",
    "calls",
    "support_portal",
    "demo",
)

# Синонимы префиксов: разные части кода писали действия по-разному, а в фильтре
# раздел должен быть один.
AUDIT_CATEGORY_ALIASES = {
    "access_assignment": "identity",
    "conversation": "conversations",
}


AUDIT_ACTION_LABELS: dict[str, str] = {
    # --- Доступ и сотрудники ---
    "identity.login_succeeded": "audit.action_identity_login_succeeded",
    "identity.login_failed": "audit.action_identity_login_failed",
    "identity.login_totp_required": "audit.action_identity_login_totp_required",
    "identity.logout": "audit.action_identity_logout",
    "identity.password_reset_requested": "audit.action_identity_password_reset_requested",
    "identity.password_reset_completed": "audit.action_identity_password_reset_completed",
    "identity.password_reset_failed": "audit.action_identity_password_reset_failed",
    "identity.temporary_password_changed": "audit.action_identity_temporary_password_changed",
    "identity.profile_updated": "audit.action_identity_profile_updated",
    "identity.profile_language_changed": "audit.action_identity_profile_language_changed",
    "identity.profile_password_changed": "audit.action_identity_profile_password_changed",
    "identity.profile_sessions_revoked": "audit.action_identity_profile_sessions_revoked",
    "identity.profile_totp_setup_started": "audit.action_identity_profile_totp_setup_started",
    "identity.profile_totp_disabled": "audit.action_identity_profile_totp_disabled",
    "identity.totp_enabled": "audit.action_identity_totp_enabled",
    "identity.totp_setup_failed": "audit.action_identity_totp_setup_failed",
    "identity.totp_verify_failed": "audit.action_identity_totp_verify_failed",
    "identity.avatar_updated": "audit.action_identity_avatar_updated",
    "identity.avatar_deleted": "audit.action_identity_avatar_deleted",
    "identity.employee_created": "audit.action_identity_employee_created",
    "identity.employee_updated": "audit.action_identity_employee_updated",
    "identity.employee_blocked": "audit.action_identity_employee_blocked",
    "identity.employee_unblocked": "audit.action_identity_employee_unblocked",
    "identity.employee_role_changed": "audit.action_identity_employee_role_changed",
    "identity.employee_groups_changed": "audit.action_identity_employee_groups_changed",
    "identity.employee_password_reset": "audit.action_identity_employee_password_reset",
    "identity.employee_sessions_terminated": "audit.action_identity_employee_sessions_terminated",
    "identity.employee_privileged_action_denied": "audit.action_identity_employee_privileged_action_denied",
    "identity.group_created": "audit.action_identity_group_created",
    "identity.group_updated": "audit.action_identity_group_updated",
    "identity.group_deleted": "audit.action_identity_group_deleted",
    "identity.ownership_transferred": "audit.action_identity_ownership_transferred",
    "identity.owner_bootstrapped": "audit.action_identity_owner_bootstrapped",
    "identity.instance_setup_completed": "audit.action_identity_instance_setup_completed",
    "identity.access_profile_created": "audit.action_identity_access_profile_created",
    "identity.access_profile_updated": "audit.action_identity_access_profile_updated",
    "identity.access_assignment_created": "audit.action_identity_access_assignment_created",
    "identity.access_assignment_revoked": "audit.action_identity_access_assignment_revoked",
    "access_assignment.created": "audit.action_access_assignment_created",
    # --- Настройки ---
    "administration.organization_updated": "audit.action_administration_organization_updated",
    "administration.logo_updated": "audit.action_administration_logo_updated",
    "administration.logo_deleted": "audit.action_administration_logo_deleted",
    "administration.communication_updated": "audit.action_administration_communication_updated",
    "administration.storage_updated": "audit.action_administration_storage_updated",
    "administration.storage_migration_requested": "audit.action_administration_storage_migration_requested",
    "administration.instance_updated": "audit.action_administration_instance_updated",
    # --- Организация ---
    "organization.provisioned": "audit.action_organization_provisioned",
    "organization.owner_activated": "audit.action_organization_owner_activated",
    "organization.owner_invitation_requested": "audit.action_organization_owner_invitation_requested",
    # --- Интеграции и каналы ---
    "integrations.integration_created": "audit.action_integrations_integration_created",
    "integrations.integration_updated": "audit.action_integrations_integration_updated",
    "integrations.integration_deleted": "audit.action_integrations_integration_deleted",
    "channels.channel_created": "audit.action_channels_channel_created",
    "channels.channel_updated": "audit.action_channels_channel_updated",
    "channels.channel_deleted": "audit.action_channels_channel_deleted",
    "channels.connection_bound": "audit.action_channels_connection_bound",
    # --- AI и знания ---
    "ai.agent_created": "audit.action_ai_agent_created",
    "ai.agent_status_changed": "audit.action_ai_agent_status_changed",
    "ai.agent_category_knowledge_selected": "audit.action_ai_agent_category_knowledge_selected",
    "ai.agent_knowledge_attached": "audit.action_ai_agent_knowledge_attached",
    "ai.agent_knowledge_detached": "audit.action_ai_agent_knowledge_detached",
    "ai.agent_portal_articles_attached": "audit.action_ai_agent_portal_articles_attached",
    "ai.agent_portal_articles_detached": "audit.action_ai_agent_portal_articles_detached",
    "ai.knowledge_created": "audit.action_ai_knowledge_created",
    "ai.knowledge_updated": "audit.action_ai_knowledge_updated",
    "ai.knowledge_deleted": "audit.action_ai_knowledge_deleted",
    "ai.knowledge_reindexed": "audit.action_ai_knowledge_reindexed",
    "ai.knowledge_imported": "audit.action_ai_knowledge_imported",
    "ai.knowledge_attachment_added": "audit.action_ai_knowledge_attachment_added",
    "ai.knowledge_attachment_deleted": "audit.action_ai_knowledge_attachment_deleted",
    "ai.knowledge_category_created": "audit.action_ai_knowledge_category_created",
    "ai.knowledge_category_updated": "audit.action_ai_knowledge_category_updated",
    "ai.knowledge_category_deleted": "audit.action_ai_knowledge_category_deleted",
    # --- Диалоги ---
    "conversations.claimed": "audit.action_conversations_claimed",
    "conversations.released_to_ai": "audit.action_conversations_released_to_ai",
    "conversations.returned_to_queue": "audit.action_conversations_returned_to_queue",
    "conversations.assignee_changed": "audit.action_conversations_assignee_changed",
    "conversations.group_changed": "audit.action_conversations_group_changed",
    "conversations.priority_changed": "audit.action_conversations_priority_changed",
    "conversations.closed": "audit.action_conversations_closed",
    "conversations.archived": "audit.action_conversations_archived",
    "conversations.unarchived": "audit.action_conversations_unarchived",
    "conversations.marked_spam": "audit.action_conversations_marked_spam",
    "conversations.contact_requested": "audit.action_conversations_contact_requested",
    "conversations.contact_updated": "audit.action_conversations_contact_updated",
    "conversation.contact_updated": "audit.action_conversation_contact_updated",
    "conversations.file_sent": "audit.action_conversations_file_sent",
    "conversations.voice_sent": "audit.action_conversations_voice_sent",
    # --- Контакты ---
    "contacts.merged": "audit.action_contacts_merged",
    "contacts.unmerged": "audit.action_contacts_unmerged",
    # --- Звонки ---
    "calls.requested": "audit.action_calls_requested",
    "calls.cancelled": "audit.action_calls_cancelled",
    # --- Порталы ---
    "support_portal.created": "audit.action_support_portal_created",
    "support_portal.published": "audit.action_support_portal_published",
    "support_portal.draft": "audit.action_support_portal_draft",
    "support_portal.articles_imported": "audit.action_support_portal_articles_imported",
    # --- Демо-данные ---
    "demo.install_requested": "audit.action_demo_install_requested",
    "demo.installed": "audit.action_demo_installed",
    "demo.installed_accounts": "audit.action_demo_installed_accounts",
    "demo.remove_requested": "audit.action_demo_remove_requested",
    "demo.removed": "audit.action_demo_removed",
}

def audit_result_label(result: str) -> str:
    """Подпись результата события или «Неизвестно» для чужого кода."""

    key = AUDIT_RESULT_LABELS.get(result)
    return t(key) if key else t("audit.result_unknown")


AUDIT_RESULT_LABELS = {
    "SUCCESS": "audit.result_success",
    "DENIED": "audit.result_denied",
    "FAILED": "audit.result_failed",
}

# Что за объект тронули: тип из модели в человеческом виде. Пусто — покажем
# сам object_type, он и так читается латиницей.
AUDIT_OBJECT_TYPE_LABELS = {
    "Organization": "audit.object_organization",
    "HumanUser": "audit.object_humanuser",
    "EmployeeGroup": "audit.object_employeegroup",
    "Integration": "audit.object_integration",
    "Channel": "audit.object_channel",
    "Knowledge": "audit.object_knowledge",
    "KnowledgeCategory": "audit.object_knowledgecategory",
    "AgentCard": "audit.object_agentcard",
    "Conversation": "audit.object_conversation",
    "Contact": "audit.object_contact",
    "SupportPortal": "audit.object_supportportal",
    "AccessProfile": "audit.object_accessprofile",
    "AccessAssignment": "audit.object_accessassignment",
    "InstanceSettings": "audit.object_instancesettings",
    "StorageSettings": "audit.object_storagesettings",
}


def audit_category(action: str) -> str:
    """Раздел действия — префикс кода до первой точки, приведённый к синониму."""

    prefix = action.split(".", 1)[0] if "." in action else ""
    return AUDIT_CATEGORY_ALIASES.get(prefix, prefix)


def audit_category_label(category: str) -> str:
    key = AUDIT_CATEGORY_LABELS.get(category)
    return t(key) if key else t("audit.category_other")


def audit_action_label(action: str) -> str:
    """Подпись действия или пустая строка.

    Пусто означает «подписи ещё нет» — интерфейс покажет сырой код. Это лучше
    заглушки «Системное действие»: по коду видно, что произошло, и видно, что
    надо дописать сюда.
    """

    key = AUDIT_ACTION_LABELS.get(action)
    return t(key) if key else ""


def audit_object_label(object_type: str, object_id: str) -> str:
    """«Сотрудник · 42» — что именно тронули. Без типа объекта строка пустая."""

    if not object_type:
        return ""
    key = AUDIT_OBJECT_TYPE_LABELS.get(object_type)
    label = t(key) if key else object_type
    return f"{label} · {object_id}" if object_id else label


def audit_categories() -> list[dict[str, str]]:
    """Разделы для фильтра — в фиксированном порядке, а не в порядке словаря."""

    return [
        {"value": key, "label": t(AUDIT_CATEGORY_LABELS[key])}
        for key in AUDIT_CATEGORY_ORDER
    ]

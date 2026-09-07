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

# Разделы журнала: по ним фильтр и группировка. Ключ — префикс кода действия
# до первой точки.
AUDIT_CATEGORY_LABELS: dict[str, str] = {
    "identity": "Доступ и сотрудники",
    "access_assignment": "Доступ и сотрудники",
    "administration": "Настройки",
    "organization": "Организация",
    "integrations": "Интеграции",
    "channels": "Каналы",
    "ai": "AI и знания",
    "conversations": "Диалоги",
    "conversation": "Диалоги",
    "contacts": "Контакты",
    "calls": "Звонки",
    "support_portal": "Порталы",
    "demo": "Демо-данные",
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
    "identity.login_succeeded": "Вход в систему",
    "identity.login_failed": "Неудачный вход",
    "identity.login_totp_required": "Запрошен код двухфакторной проверки",
    "identity.logout": "Выход из системы",
    "identity.password_reset_requested": "Запрошен сброс пароля",
    "identity.password_reset_completed": "Пароль восстановлен",
    "identity.password_reset_failed": "Неудачный сброс пароля",
    "identity.temporary_password_changed": "Сменён временный пароль",
    "identity.profile_updated": "Изменён профиль сотрудника",
    "identity.profile_password_changed": "Изменён пароль",
    "identity.profile_sessions_revoked": "Завершены свои сессии",
    "identity.profile_totp_setup_started": "Начата настройка двухфакторной проверки",
    "identity.profile_totp_disabled": "Отключена двухфакторная проверка",
    "identity.totp_enabled": "Включена двухфакторная проверка",
    "identity.totp_setup_failed": "Ошибка настройки двухфакторной проверки",
    "identity.totp_verify_failed": "Неверный код двухфакторной проверки",
    "identity.avatar_updated": "Изменено фото профиля",
    "identity.avatar_deleted": "Удалено фото профиля",
    "identity.employee_created": "Добавлен сотрудник",
    "identity.employee_updated": "Изменён сотрудник",
    "identity.employee_blocked": "Сотрудник заблокирован",
    "identity.employee_unblocked": "Сотрудник разблокирован",
    "identity.employee_role_changed": "Изменена роль сотрудника",
    "identity.employee_groups_changed": "Изменены группы сотрудника",
    "identity.employee_password_reset": "Сброшен пароль сотрудника",
    "identity.employee_sessions_terminated": "Завершены сессии сотрудника",
    "identity.employee_privileged_action_denied": "Отказано в привилегированном действии",
    "identity.group_created": "Создана группа",
    "identity.group_updated": "Изменена группа",
    "identity.group_deleted": "Удалена группа",
    "identity.ownership_transferred": "Передано владение организацией",
    "identity.owner_bootstrapped": "Создан владелец установки",
    "identity.instance_setup_completed": "Пройден мастер первого запуска",
    "identity.access_profile_created": "Создан профиль доступа",
    "identity.access_profile_updated": "Изменён профиль доступа",
    "identity.access_assignment_created": "Назначен доступ сотруднику",
    "identity.access_assignment_revoked": "Отозван доступ сотрудника",
    "access_assignment.created": "Назначен доступ сотруднику",
    # --- Настройки ---
    "administration.organization_updated": "Изменены данные организации",
    "administration.logo_updated": "Изменён логотип организации",
    "administration.logo_deleted": "Удалён логотип организации",
    "administration.communication_updated": "Изменены голосовые и звонки",
    "administration.storage_updated": "Изменено хранилище файлов",
    "administration.storage_migration_requested": "Запущен перенос файлов",
    "administration.instance_updated": "Изменены настройки платформы",
    # --- Организация ---
    "organization.provisioned": "Создана организация",
    "organization.owner_activated": "Активирован владелец организации",
    "organization.owner_invitation_requested": "Отправлено приглашение владельцу",
    # --- Интеграции и каналы ---
    "integrations.integration_created": "Добавлена интеграция",
    "integrations.integration_updated": "Изменена интеграция",
    "integrations.integration_deleted": "Удалена интеграция",
    "channels.channel_created": "Создан канал",
    "channels.channel_updated": "Изменён канал",
    "channels.channel_deleted": "Удалён канал",
    "channels.connection_bound": "Подключение привязано к агенту",
    # --- AI и знания ---
    "ai.agent_created": "Создан агент",
    "ai.agent_status_changed": "Изменён статус агента",
    "ai.agent_category_knowledge_selected": "Выбраны знания категории для агента",
    "ai.agent_knowledge_attached": "Знания подключены к агенту",
    "ai.agent_knowledge_detached": "Знания отключены от агента",
    "ai.agent_portal_articles_attached": "Статьи портала подключены к агенту",
    "ai.agent_portal_articles_detached": "Статьи портала отключены от агента",
    "ai.knowledge_created": "Добавлено знание",
    "ai.knowledge_updated": "Изменено знание",
    "ai.knowledge_deleted": "Удалено знание",
    "ai.knowledge_reindexed": "Знание переиндексировано",
    "ai.knowledge_imported": "Знания импортированы",
    "ai.knowledge_attachment_added": "Добавлено вложение знания",
    "ai.knowledge_attachment_deleted": "Удалено вложение знания",
    "ai.knowledge_category_created": "Создана категория знаний",
    "ai.knowledge_category_updated": "Изменена категория знаний",
    "ai.knowledge_category_deleted": "Удалена категория знаний",
    # --- Диалоги ---
    "conversations.claimed": "Диалог взят в работу",
    "conversations.released_to_ai": "Диалог возвращён AI",
    "conversations.returned_to_queue": "Диалог возвращён в очередь",
    "conversations.assignee_changed": "Изменён ответственный за диалог",
    "conversations.group_changed": "Изменена группа диалога",
    "conversations.priority_changed": "Изменён приоритет диалога",
    "conversations.closed": "Диалог закрыт",
    "conversations.archived": "Диалог отправлен в архив",
    "conversations.unarchived": "Диалог возвращён из архива",
    "conversations.marked_spam": "Диалог помечен спамом",
    "conversations.contact_requested": "Запрошены контакты клиента",
    "conversations.contact_updated": "Изменён контакт диалога",
    "conversation.contact_updated": "Изменён контакт диалога",
    "conversations.file_sent": "Отправлен файл в диалог",
    "conversations.voice_sent": "Отправлено голосовое в диалог",
    # --- Контакты ---
    "contacts.merged": "Объединение контактов",
    "contacts.unmerged": "Разъединение контактов",
    # --- Звонки ---
    "calls.requested": "Запрошен звонок",
    "calls.cancelled": "Звонок отменён",
    # --- Порталы ---
    "support_portal.created": "Создан портал",
    "support_portal.published": "Портал опубликован",
    "support_portal.draft": "Портал снят с публикации",
    "support_portal.articles_imported": "Импортированы статьи портала",
    # --- Демо-данные ---
    "demo.install_requested": "Запрошена установка демо-данных",
    "demo.installed": "Демо-данные установлены",
    "demo.installed_accounts": "Созданы учётные записи демо-сотрудников",
    "demo.remove_requested": "Запрошено удаление демо-данных",
    "demo.removed": "Демо-данные удалены",
}

AUDIT_RESULT_LABELS = {
    "SUCCESS": "Выполнено",
    "DENIED": "Отклонено",
    "FAILED": "Ошибка",
}

# Что за объект тронули: тип из модели в человеческом виде. Пусто — покажем
# сам object_type, он и так читается латиницей.
AUDIT_OBJECT_TYPE_LABELS = {
    "Organization": "Организация",
    "HumanUser": "Сотрудник",
    "EmployeeGroup": "Группа",
    "Integration": "Интеграция",
    "Channel": "Канал",
    "Knowledge": "Знание",
    "KnowledgeCategory": "Категория знаний",
    "AgentCard": "Агент",
    "Conversation": "Диалог",
    "Contact": "Контакт",
    "SupportPortal": "Портал",
    "AccessProfile": "Профиль доступа",
    "AccessAssignment": "Назначение доступа",
    "InstanceSettings": "Установка",
    "StorageSettings": "Хранилище",
}


def audit_category(action: str) -> str:
    """Раздел действия — префикс кода до первой точки, приведённый к синониму."""

    prefix = action.split(".", 1)[0] if "." in action else ""
    return AUDIT_CATEGORY_ALIASES.get(prefix, prefix)


def audit_category_label(category: str) -> str:
    return AUDIT_CATEGORY_LABELS.get(category, "Прочее")


def audit_action_label(action: str) -> str:
    """Подпись действия или пустая строка.

    Пусто означает «подписи ещё нет» — интерфейс покажет сырой код. Это лучше
    заглушки «Системное действие»: по коду видно, что произошло, и видно, что
    надо дописать сюда.
    """

    return AUDIT_ACTION_LABELS.get(action, "")


def audit_object_label(object_type: str, object_id: str) -> str:
    """«Сотрудник · 42» — что именно тронули. Без типа объекта строка пустая."""

    if not object_type:
        return ""
    label = AUDIT_OBJECT_TYPE_LABELS.get(object_type, object_type)
    return f"{label} · {object_id}" if object_id else label


def audit_categories() -> list[dict[str, str]]:
    """Разделы для фильтра — в фиксированном порядке, а не в порядке словаря."""

    return [
        {"value": key, "label": AUDIT_CATEGORY_LABELS[key]}
        for key in AUDIT_CATEGORY_ORDER
    ]

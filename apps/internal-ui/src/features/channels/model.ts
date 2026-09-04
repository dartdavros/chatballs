import type { Channel, ChannelPolicy, PolicyFlag, PolicyPreset } from "./types";
import type { StatusPillKey } from "../../shared/ui";
import { formatRussianCount } from "../../shared/text";

export const POLICY_FLAGS: PolicyFlag[] = [
  "requiresAuthenticatedProductIdentity",
  "allowAnonymousSessions",
  "allowSelfReportedContact",
  "allowSalesAttribution",
  "allowCheckoutActions",
];

/** Однострочное пояснение следствия каждого флага (SPEC-HUB-0027 §11.2). */
export const POLICY_LABELS: Record<PolicyFlag, { title: string; hint: string }> = {
  requiresAuthenticatedProductIdentity: {
    title: "Обязательная продуктовая идентичность",
    hint: "Диалог требует авторизации как владелец продукта.",
  },
  allowAnonymousSessions: {
    title: "Анонимные сессии",
    hint: "Разрешает диалоги без идентификации пользователя.",
  },
  allowSelfReportedContact: {
    title: "Самозаявленный контакт",
    hint: "Позволяет пользователю указать контакт вручную.",
  },
  allowSalesAttribution: {
    title: "Связь продаж с диалогами",
    hint: "Связывает продажу с диалогом канала.",
  },
  allowCheckoutActions: {
    title: "Оформление заказа в диалоге",
    hint: "Разрешает оформление заказа в диалоге.",
  },
};

export const PRESETS: Record<Exclude<PolicyPreset, "CUSTOM">, ChannelPolicy> = {
  SALES: {
    requiresAuthenticatedProductIdentity: false,
    allowAnonymousSessions: true,
    allowSelfReportedContact: true,
    allowSalesAttribution: true,
    allowCheckoutActions: true,
  },
  SUPPORT: {
    requiresAuthenticatedProductIdentity: true,
    allowAnonymousSessions: false,
    allowSelfReportedContact: false,
    allowSalesAttribution: false,
    allowCheckoutActions: false,
  },
};

export const OPERATOR_POLICY: ChannelPolicy = {
  requiresAuthenticatedProductIdentity: false,
  allowAnonymousSessions: true,
  allowSelfReportedContact: true,
  allowSalesAttribution: false,
  allowCheckoutActions: false,
};

/** Состояние подключения приходит строкой — на экран идёт словарь, не энум. */
export const CONNECTION_STATUS = {
  OK: "healthy",
  ERROR: "error",
  PENDING: "pending",
  UNCHECKED: "unchecked",
} as const;

export type ConnectionStatusKey = typeof CONNECTION_STATUS[keyof typeof CONNECTION_STATUS];

export function connectionStatus(status: string): ConnectionStatusKey {
  return CONNECTION_STATUS[status as keyof typeof CONNECTION_STATUS] ?? "unchecked";
}

const AGENT_STATUS: Record<string, StatusPillKey> = {
  ACTIVE: "active",
  ARCHIVED: "archived",
  DISABLED: "disabled",
  DRAFT: "draft",
};

export function agentStatus(status: string): StatusPillKey {
  return AGENT_STATUS[status] ?? "draft";
}

/**
 * Причина недоступности флага.
 *
 * `needsProduct` включает ссылку-починку «Назначить продукт» — причина без
 * способа её устранить бесполезна пользователю.
 */
export type FlagLock = { rule: string; reason: string; fix: string; needsProduct: boolean } | null;

/**
 * Причина, по которой флаг запрещён инвариантом при текущем состоянии канала.
 *
 * Выводится из продукта и обязательной идентичности, а не приходит с сервера:
 * правила P1-P5 детерминированы, а источником прав остаётся backend — он
 * отклоняет запрос независимо от того, что показал интерфейс. Показать причину
 * обязательно: флаг не должен молча игнорироваться при сохранении (§11.2).
 */
export function flagLock(flag: PolicyFlag, policy: ChannelPolicy, hasProduct: boolean): FlagLock {
  if (!hasProduct) {
    if (flag === "allowCheckoutActions") {
      return {
        rule: "P1",
        reason: "Коммерческие действия недоступны непродуктовому каналу",
        fix: "Назначьте продукт каналу, чтобы включить.",
        needsProduct: true,
      };
    }
    if (flag === "allowSalesAttribution") {
      return {
        rule: "P2",
        reason: "Связь продаж с диалогами недоступна непродуктовому каналу",
        fix: "Свяжите канал с продуктом, чтобы включить.",
        needsProduct: true,
      };
    }
    if (flag === "requiresAuthenticatedProductIdentity") {
      return {
        rule: "P3",
        reason: "Продуктовая идентичность требует продукта",
        fix: "Назначьте продукт каналу, чтобы включить.",
        needsProduct: true,
      };
    }
  }
  if (policy.requiresAuthenticatedProductIdentity) {
    if (flag === "allowAnonymousSessions") {
      return {
        rule: "P4",
        reason: "Анонимные сессии несовместимы с обязательной идентичностью",
        fix: "Выключите обязательную идентичность, чтобы включить.",
        needsProduct: false,
      };
    }
    if (flag === "allowSelfReportedContact") {
      return {
        rule: "P5",
        reason: "Самозаявленный контакт несовместим с обязательной идентичностью",
        fix: "Выключите обязательную идентичность, чтобы включить.",
        needsProduct: false,
      };
    }
  }
  return null;
}

/** Пресет, которому соответствует текущий набор флагов, иначе «Свой». */
export function presetOf(policy: ChannelPolicy): PolicyPreset {
  const same = (preset: ChannelPolicy) =>
    POLICY_FLAGS.every((flag) => preset[flag] === policy[flag]);
  if (same(PRESETS.SALES)) return "SALES";
  if (same(PRESETS.SUPPORT)) return "SUPPORT";
  return "CUSTOM";
}

export const PRESET_LABELS: Record<PolicyPreset, string> = {
  SALES: "Продажи",
  SUPPORT: "Поддержка",
  CUSTOM: "Свой",
};

/** `code` попадает в embed-URL виджета, поэтому только латиница, цифры и дефис. */
export function slugify(name: string): string {
  const map: Record<string, string> = {
    а: "a", б: "b", в: "v", г: "g", д: "d", е: "e", ё: "e", ж: "zh", з: "z",
    и: "i", й: "i", к: "k", л: "l", м: "m", н: "n", о: "o", п: "p", р: "r",
    с: "s", т: "t", у: "u", ф: "f", х: "h", ц: "c", ч: "ch", ш: "sh", щ: "sch",
    ъ: "", ы: "y", ь: "", э: "e", ю: "yu", я: "ya",
  };
  return name
    .toLowerCase()
    .split("")
    .map((char) => map[char] ?? char)
    .join("")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 64);
}

export const BLOCKER_LABELS: Record<string, string> = {
  conversations: "Диалоги",
  orders: "Заказы",
  attributionTokens: "Связи продаж с диалогами",
  connections: "Подключения",
  supportContracts: "Договоры поддержки",
  agent: "Агент",
  llmInvocations: "История работы AI",
};

/**
 * Почему канал нельзя удалить — по данным строки списка.
 *
 * Это подсказка интерфейса, а не решение: удаление всё равно проверяет
 * backend. Она нужна, чтобы недоступный пункт меню объяснял себя.
 */
export function deletionHint(channel: Channel): string | null {
  const parts: string[] = [];
  if (channel.counters.openConversations > 0) {
    parts.push(formatRussianCount(channel.counters.openConversations, "диалог", "диалога", "диалогов"));
  }
  if (channel.counters.connections > 0) {
    parts.push(formatRussianCount(channel.counters.connections, "подключение", "подключения", "подключений"));
  }
  if (channel.agent) parts.push("агент");
  return parts.length ? `Нельзя: ${parts.join(", ")}` : null;
}

export function blockerSummary(blockers: { type: string; count: number }[]): string {
  return blockers
    .map((item) => `${(BLOCKER_LABELS[item.type] ?? "связанные записи").toLowerCase()}: ${item.count}`)
    .join(", ");
}

export type GroupTab = { key: string; label: string; count: number };

/** Табы идут в порядке групп компании; «Без группы» присутствует даже при нуле. */
export function groupTabs(
  channels: Channel[],
  groups: Array<{ id: number; name: string }>,
): GroupTab[] {
  const countOf = (groupId: number | null) =>
    channels.filter((channel) => channel.groupId === groupId).length;
  return [
    { key: "all", label: "Все", count: channels.length },
    ...groups.map((group) => ({
      key: String(group.id),
      label: group.name,
      count: countOf(group.id),
    })),
    { key: "none", label: "Без группы", count: countOf(null) },
  ];
}

export const channelCountLabel = (value: number) => formatRussianCount(value, "канал", "канала", "каналов");
export const archivedCountLabel = (value: number) => formatRussianCount(value, "архивный", "архивных", "архивных");

export function filterChannels(
  channels: Channel[],
  { tab, search, showArchived }: { tab: string; search: string; showArchived: boolean },
): Channel[] {
  const query = search.trim().toLowerCase();
  return channels.filter((channel) => {
    if (!showArchived && !channel.isActive) return false;
    if (tab === "none" && channel.groupId !== null) return false;
    if (tab !== "all" && tab !== "none" && String(channel.groupId) !== tab) return false;
    if (!query) return true;
    return (
      channel.name.toLowerCase().includes(query) || channel.code.toLowerCase().includes(query)
    );
  });
}

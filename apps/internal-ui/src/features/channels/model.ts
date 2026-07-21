import type { Channel, ChannelPolicy, PolicyFlag, PolicyPreset } from "./types";

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
    title: "Attribution продаж",
    hint: "Связывает продажу с диалогом канала.",
  },
  allowCheckoutActions: {
    title: "Коммерческие действия (checkout)",
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

export type FlagLock = { rule: string; reason: string; fix?: string } | null;

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
      };
    }
    if (flag === "allowSalesAttribution") {
      return {
        rule: "P2",
        reason: "Attribution недоступна непродуктовому каналу",
        fix: "Свяжите канал с продуктом, чтобы включить.",
      };
    }
    if (flag === "requiresAuthenticatedProductIdentity") {
      return {
        rule: "P3",
        reason: "Продуктовая идентичность требует продукта",
        fix: "Назначьте продукт каналу, чтобы включить.",
      };
    }
  }
  if (policy.requiresAuthenticatedProductIdentity) {
    if (flag === "allowAnonymousSessions") {
      return {
        rule: "P4",
        reason: "Анонимные сессии несовместимы с обязательной идентичностью",
        fix: "Выключите обязательную идентичность, чтобы включить.",
      };
    }
    if (flag === "allowSelfReportedContact") {
      return {
        rule: "P5",
        reason: "Самозаявленный контакт несовместим с обязательной идентичностью",
        fix: "Выключите обязательную идентичность, чтобы включить.",
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
  attributionTokens: "Attribution-токены",
  connections: "Подключения",
  supportContracts: "Support-контракты",
  agent: "Агент",
  llmInvocations: "Вызовы LLM",
};

export function blockerSummary(blockers: { type: string; count: number }[]): string {
  return blockers
    .map((item) => `${(BLOCKER_LABELS[item.type] ?? item.type).toLowerCase()}: ${item.count}`)
    .join(", ");
}

export type DepartmentTab = { key: string; label: string; count: number };

/** Табы-фильтры: Все, по одному на отдел видимых каналов, Без отдела (§11.1). */
export function departmentTabs(channels: Channel[]): DepartmentTab[] {
  const byDepartment = new Map<string, { label: string; count: number }>();
  let orphans = 0;
  for (const channel of channels) {
    if (channel.departmentId === null) {
      orphans += 1;
      continue;
    }
    const key = String(channel.departmentId);
    const existing = byDepartment.get(key);
    const label = channel.departmentName ?? channel.department ?? key;
    byDepartment.set(key, { label, count: (existing?.count ?? 0) + 1 });
  }
  const tabs: DepartmentTab[] = [{ key: "all", label: "Все", count: channels.length }];
  for (const [key, value] of [...byDepartment.entries()].sort((a, b) =>
    a[1].label.localeCompare(b[1].label, "ru"),
  )) {
    tabs.push({ key, label: value.label, count: value.count });
  }
  if (orphans) tabs.push({ key: "none", label: "Без отдела", count: orphans });
  return tabs;
}

export function filterChannels(
  channels: Channel[],
  { tab, search, showArchived }: { tab: string; search: string; showArchived: boolean },
): Channel[] {
  const query = search.trim().toLowerCase();
  return channels.filter((channel) => {
    if (!showArchived && !channel.isActive) return false;
    if (tab === "none" && channel.departmentId !== null) return false;
    if (tab !== "all" && tab !== "none" && String(channel.departmentId) !== tab) return false;
    if (!query) return true;
    return (
      channel.name.toLowerCase().includes(query) || channel.code.toLowerCase().includes(query)
    );
  });
}

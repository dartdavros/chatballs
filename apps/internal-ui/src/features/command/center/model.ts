import { api } from "../../../api/client";
import type { CommandPeriod, MetricItem } from "./types";

// Реальная сводка командного центра (conversations/command.py) — без мок-данных.

export type ApiDialogBlock = { open: number; activeNow: number; onAI: number; onOperators: number; waiting: number };
export type ApiDepartment = {
  code: string;
  name: string;
  route: string;
  employees: number;
  aiAgents: number;
  dialogs: ApiDialogBlock;
};
export type ApiCommandOverview = {
  period: CommandPeriod;
  generatedAt: string;
  company: { status: "ok" | "attention" | "critical"; departments: number; openDialogs: number };
  departments: ApiDepartment[];
  attention: Array<{ kind: "dialog" | "integration"; title: string; meta: string; minutes: number }>;
  integrations: Array<{ name: string; group: string; status: "OK" | "ERROR" | "UNCHECKED" }>;
  ai: { spendMicros: number; dailyLimitMicros: number; tokens: number; dialogs: number };
};

export const fetchCommandOverview = (period: CommandPeriod) =>
  api<ApiCommandOverview>(`/api/v1/conversations/command-overview/?period=${period}`);

const usd = (micros: number) => `$${(micros / 1_000_000).toLocaleString("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

function tokensLabel(tokens: number): string {
  if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toLocaleString("ru-RU", { maximumFractionDigits: 1 })}M`;
  if (tokens >= 1_000) return `${Math.round(tokens / 1_000)}K`;
  return String(tokens);
}

function timeLabel(minutes: number): string {
  if (minutes < 60) return `${minutes} мин`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} ч`;
  return `${Math.floor(hours / 24)} д`;
}

export type StatusMeta = { label: string; color: string; bg: string; border: string; dot: string };

const STATUS_META: Record<ApiCommandOverview["company"]["status"], StatusMeta> = {
  ok: { label: "Штатно", color: "var(--success-text)", bg: "var(--success-bg)", border: "var(--success-border)", dot: "var(--success)" },
  attention: { label: "Требует внимания", color: "var(--warning-text)", bg: "var(--warning-bg-strong)", border: "var(--warning-border)", dot: "var(--warning)" },
  critical: { label: "Критично", color: "var(--error-text)", bg: "var(--error-bg)", border: "var(--error-border)", dot: "var(--error)" },
};

const COMPANY_SUMMARY: Record<ApiCommandOverview["company"]["status"], string> = {
  ok: "Все системы в норме, критичных событий нет.",
  attention: "Есть события, требующие внимания оператора.",
  critical: "Есть критичные проблемы — проверьте раздел «Требует внимания».",
};

const ATTENTION_DOT: Record<string, string> = { dialog: "var(--warning)", integration: "var(--error)" };

const INTEGRATION_STATUS: Record<string, { label: string; color: string }> = {
  OK: { label: "Подключено", color: "var(--success)" },
  ERROR: { label: "Ошибка", color: "var(--error)" },
  UNCHECKED: { label: "Не проверено", color: "var(--n-4)" },
};

const PERIOD_LABEL: Record<CommandPeriod, string> = { today: "Сегодня", d7: "7 дней", d30: "30 дней" };

export type DepartmentVm = {
  code: string;
  name: string;
  route: string;
  icon: "shop" | "wrench";
  subtitle: string;
  status: StatusMeta;
  summary: string;
  dialogItems: MetricItem[];
};

export function commandCenterModel(data: ApiCommandOverview) {
  const st = STATUS_META[data.company.status];
  const periodLabel = PERIOD_LABEL[data.period];

  const departments: DepartmentVm[] = data.departments.map((department) => {
    const d = department.dialogs;
    return {
      code: department.code,
      name: department.name,
      route: department.route,
      icon: department.name === "Поддержка" ? "wrench" : "shop",
      subtitle: `Сотрудники: ${department.employees} · Агенты: ${department.aiAgents}`,
      status: d.waiting > 0 ? STATUS_META.attention : STATUS_META.ok,
      summary: d.waiting > 0 ? `В очереди ${d.waiting} — нужен оператор.` : "Очередь оператора пуста.",
      dialogItems: [
        { label: "Открытые диалоги", value: String(d.open) },
        { label: "Активны за 15 мин", value: String(d.activeNow) },
        { label: "На AI", value: String(d.onAI), dot: "var(--ai)" },
        { label: "На операторах", value: String(d.onOperators), dot: "var(--primary)" },
        { label: "Ожидают оператора", value: String(d.waiting), color: d.waiting > 0 ? "var(--warning-text)" : "var(--text-body)" },
      ],
    };
  });

  const attention = data.attention.map((item) => ({
    dot: ATTENTION_DOT[item.kind] ?? "var(--warning)",
    title: item.title,
    meta: item.meta,
    time: timeLabel(item.minutes),
  }));

  const integrations = data.integrations.map((item) => {
    const status = INTEGRATION_STATUS[item.status] ?? INTEGRATION_STATUS.UNCHECKED;
    return { name: item.name, group: item.group, dot: status.color, statusLabel: status.label, statusColor: status.color };
  });
  const okCount = data.integrations.filter((item) => item.status === "OK").length;

  // Прогресс бюджета осмыслен только для «Сегодня» и при заданном дневном лимите.
  const hasBudget = data.period === "today" && data.ai.dailyLimitMicros > 0;
  const aiPct = hasBudget ? Math.min(100, Math.round((data.ai.spendMicros / data.ai.dailyLimitMicros) * 100)) : 0;

  return {
    st,
    compSummary: COMPANY_SUMMARY[data.company.status],
    banner: {
      departments: String(data.company.departments),
      open: String(data.company.openDialogs),
    },
    departments,
    attention,
    integrations,
    okCount: `${okCount}/${data.integrations.length} в норме`,
    intHeadColor: okCount === data.integrations.length ? "var(--success-text)" : "var(--warning-text)",
    periodLabel,
    periodLabelUpper: periodLabel.toUpperCase(),
    aiSpendStr: usd(data.ai.spendMicros),
    budgetStr: hasBudget ? usd(data.ai.dailyLimitMicros) : "",
    hasBudget,
    aiPct,
    aiBarColor: aiPct >= 85 ? "var(--error)" : aiPct >= 70 ? "var(--warning)" : "var(--primary)",
    aiTokens: tokensLabel(data.ai.tokens),
    aiDialogs: String(data.ai.dialogs),
    costPerDialog: data.ai.dialogs > 0 ? usd(data.ai.spendMicros / data.ai.dialogs) : "—",
    generatedAt: new Date(data.generatedAt).toLocaleString("ru-RU", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }),
  };
}

export type CommandVm = ReturnType<typeof commandCenterModel>;

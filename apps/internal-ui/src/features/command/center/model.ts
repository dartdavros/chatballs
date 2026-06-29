import type { CommandPeriod } from "./types";

export function commandCenterModel(period: CommandPeriod) {
  const fmt = (n: number) => `₽${Math.round(n).toLocaleString("ru-RU").replace(/\u00a0/g, " ")}`;
  const ops = { open: 42, active: 9, ai: 35, op: 7, wait: 0, pend: 1, ferr: 0 };
  const com = {
    today: { label: "Сегодня", sales: 18, rev: 146200, aiSpend: 1240, budget: 5000, tokens: "412K", dlg: 42 },
    d7: { label: "7 дней", sales: 126, rev: 1024600, aiSpend: 8600, budget: 35000, tokens: "2,9M", dlg: 318 },
    d30: { label: "30 дней", sales: 540, rev: 4386000, aiSpend: 36400, budget: 150000, tokens: "12,4M", dlg: 1342 },
  }[period];
  const st = { label: "Нормально", color: "#389e0d", bg: "#f6ffed", border: "#b7eb8f", dot: "#52c41a" };
  const m = {
    open: String(ops.open),
    active: String(ops.active),
    ai: String(ops.ai),
    op: String(ops.op),
    wait: String(ops.wait),
    pend: String(ops.pend),
    ferr: String(ops.ferr),
    sales: String(com.sales),
    rev: fmt(com.rev),
    waitColor: "#262626",
    pendColor: "#262626",
    ferrColor: "#262626",
  };
  const attention = [
    { dot: "#faad14", title: "Незавершённый платёж · заказ ORD-10482", meta: "Продажи · Точка", time: "6 мин" },
    { dot: "#1677ff", title: "Подписка истекает через 2 дня · Foxray Про", meta: "Продажи", time: "1 ч" },
  ];
  const integrations = [
    { name: "OpenRouter", group: "AI-провайдер", dot: "#52c41a", statusLabel: "Подключено", statusColor: "#52c41a" },
    { name: "MAX", group: "Канал", dot: "#52c41a", statusLabel: "Подключено", statusColor: "#52c41a" },
    { name: "Telegram", group: "Канал", dot: "#52c41a", statusLabel: "Подключено", statusColor: "#52c41a" },
    { name: "Web Chat", group: "Канал", dot: "#52c41a", statusLabel: "Подключено", statusColor: "#52c41a" },
    { name: "FirePage", group: "Коммерческая интеграция", dot: "#52c41a", statusLabel: "Подключено", statusColor: "#52c41a" },
    { name: "Foxray", group: "Коммерческая интеграция", dot: "#52c41a", statusLabel: "Подключено", statusColor: "#52c41a" },
  ];
  const aiPct = Math.round((com.aiSpend / com.budget) * 100);
  const aiBarColor = aiPct >= 85 ? "#ff4d4f" : aiPct >= 70 ? "#faad14" : "#1677ff";
  return {
    st,
    m,
    compSummary: "Все системы в норме. Один отдел активен, критичных событий нет.",
    deptSummary: "AI ведёт большинство диалогов. Очередь оператора пуста, незавершённых задач почти нет.",
    attention,
    integrations,
    okCount: "6",
    intHeadColor: "#389e0d",
    periodLabel: com.label,
    periodLabelUpper: com.label.toUpperCase(),
    aiSpendStr: fmt(com.aiSpend),
    budgetStr: fmt(com.budget),
    aiPct,
    aiBarColor,
    aiTokens: com.tokens,
    aiDialogs: String(com.dlg),
    costPerDialog: fmt(com.aiSpend / com.dlg),
  };
}

export type CommandVm = ReturnType<typeof commandCenterModel>;

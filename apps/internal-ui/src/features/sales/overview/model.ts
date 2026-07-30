import { chartPaths } from "./chart";
import type { KpiItem, SalesListItem, SalesPeriod } from "./types";

// Реальная агрегация обзора (бэкенд: conversations/stats.py). Продажи/выручка/
// конверсия отсутствуют как домен — показываем «—», не выдумываем числа.
export type SalesStats = {
  waiting: number;
  ops: { openDialogs: number; activeNow: number; onAI: number; onOperators: number; waiting: number };
  period: {
    dialogs: number; dialogsPrev: number; messages: number;
    aiCostMicros: number; aiCostPrevMicros: number;
    sales: number; salesPrev: number; revenueMinor: number; revenuePrevMinor: number; conversion: number;
  };
  byChannel: Array<{ code: string; name: string; openDialogs: number; dialogs: number }>;
  byProduct: Array<{ code: string; name: string; openDialogs: number; dialogs: number; sales: number; revenueMinor: number }>;
  chart: { values: number[]; labels: string[] };
  problems: Array<{ conversationId: number; title: string; meta: string; minutes: number }>;
};

const DASH = "—";
const UP = "#389e0d";
const DOWN = "#cf1322";
const CHANNEL_COLORS = ["#6b5be0", "#2f8fd0", "#0f9b8e", "#d48806", "#cf1322"];

const usd = (micros: number) => `$${(micros / 1_000_000).toLocaleString("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const rub = (minor: number) => `₽${Math.round(minor / 100).toLocaleString("ru-RU").replace(/ /g, " ")}`;

function delta(current: number, previous: number): { deltaText: string; deltaColor: string; down: boolean } | null {
  if (previous <= 0) return null;
  const pct = Math.round(((current - previous) / previous) * 100);
  return { deltaText: `${pct >= 0 ? "+" : ""}${pct}%`, deltaColor: pct >= 0 ? UP : DOWN, down: pct < 0 };
}

function minutesLabel(minutes: number): string {
  if (minutes < 60) return `${minutes} мин`;
  return `${Math.floor(minutes / 60)} ч`;
}

const share = (value: number, total: number) => (total > 0 ? Math.round((value / total) * 100) : 0);

export function buildSalesOverviewVm(period: SalesPeriod, stats: SalesStats) {
  const periodLabel = { today: "Сегодня", d7: "7 дней", d30: "30 дней" }[period];
  const { ops } = stats;
  const { dialogs, dialogsPrev, messages, aiCostMicros, aiCostPrevMicros, sales, salesPrev, revenueMinor, revenuePrevMinor, conversion } = stats.period;

  const opsKpi: KpiItem[] = [
    { label: "Открытые диалоги", value: String(ops.openDialogs), sub: "в работе" },
    { label: "Активные сейчас", value: String(ops.activeNow), sub: "за 15 минут" },
    { label: "На AI", value: String(ops.onAI), sub: `${share(ops.onAI, ops.openDialogs)}% диалогов`, dot: "#722ed1" },
    { label: "На операторах", value: String(ops.onOperators), sub: `${share(ops.onOperators, ops.openDialogs)}% диалогов`, dot: "#1677ff" },
    { label: "Ожидают оператора", value: String(ops.waiting), valueColor: ops.waiting === 0 ? UP : DOWN, sub: ops.waiting === 0 ? "очередь пуста" : "в очереди", subColor: ops.waiting === 0 ? UP : DOWN },
  ];

  const dialogsDelta = delta(dialogs, dialogsPrev);
  const costDelta = delta(aiCostMicros, aiCostPrevMicros);
  const resKpi: KpiItem[] = [
    { label: "Продажи", value: String(sales), sub: "к пред.", ...(delta(sales, salesPrev) ?? {}) },
    { label: "Выручка", value: rub(revenueMinor), sub: "к пред.", ...(delta(revenueMinor, revenuePrevMinor) ?? {}) },
    { label: "Конверсия", value: `${conversion.toLocaleString("ru-RU")}%`, sub: "оплат к диалогам" },
    { label: "Стоимость AI", value: usd(aiCostMicros), sub: "к пред.", ...(costDelta ?? {}) },
    { label: "Диалоги", value: String(dialogs), sub: "к пред.", ...(dialogsDelta ?? {}) },
  ];

  const chart = chartPaths(stats.chart.values.length ? stats.chart.values : [0]);
  const openTotal = stats.byChannel.reduce((sum, channel) => sum + channel.openDialogs, 0);
  const channels = stats.byChannel.map((channel, index) => ({
    name: channel.name,
    color: CHANNEL_COLORS[index % CHANNEL_COLORS.length],
    open: String(channel.openDialogs),
    period: String(channel.dialogs),
    share: share(channel.openDialogs, openTotal),
  }));

  const products = stats.byProduct.map((product) => ({
    name: product.name,
    status: "Активен",
    sales: String(product.sales),
    rev: product.revenueMinor > 0 ? rub(product.revenueMinor) : DASH,
    conv: product.dialogs > 0 ? `${Math.round((product.sales / product.dialogs) * 100)}%` : DASH,
    dlg: String(product.dialogs),
  }));

  const problems: SalesListItem[] = stats.problems.map((problem) => ({
    dot: problem.minutes >= 30 ? DOWN : "#faad14",
    title: problem.title,
    meta: problem.meta,
    time: minutesLabel(problem.minutes),
    conversationId: problem.conversationId,
  }));

  return {
    periodLabel,
    opsKpi,
    resKpi,
    products,
    channels,
    actors: {
      aiDialogs: String(ops.onAI),
      aiCost: usd(aiCostMicros),
      operatorDialogs: String(ops.onOperators),
      waiting: String(ops.waiting),
    },
    chartTotal: String(dialogs),
    chartDelta: dialogsDelta,
    xLabels: stats.chart.labels,
    ...chart,
    problems,
  };
}

export type SalesOverviewVm = ReturnType<typeof buildSalesOverviewVm>;

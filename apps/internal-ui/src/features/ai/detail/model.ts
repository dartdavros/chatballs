import type { AiAgent } from "../model";

export type AiAgentDetail = AiAgent & {
  createdAt: string;
  updatedAt: string;
};

export type AgentTab = "overview" | "instructions" | "knowledge" | "metrics";

export const agentTabs: Array<{ key: AgentTab; label: string }> = [
  { key: "overview", label: "Обзор" },
  { key: "instructions", label: "Инструкции" },
  { key: "knowledge", label: "Знания" },
  { key: "metrics", label: "Метрики" },
];

// agent.limits — единый поддерживаемый лимит: дневной бюджет в целых центах USD (dailyCostUsd).
export function dailyBudget(limits: Record<string, unknown>): string {
  const cents = limits?.dailyCostUsd;
  if (typeof cents !== "number" || cents <= 0) return "—";
  return `$${(cents / 100).toLocaleString("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} / день`;
}

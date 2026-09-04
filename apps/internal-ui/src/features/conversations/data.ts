import type { ControlMode, DialogMode, StatusInfo } from "./types";

export const modeDots: Record<DialogMode, string> = {
  wait: "var(--warning)",
  ai: "var(--ai)",
  operator: "var(--primary)",
  closed: "var(--n-5)",
};

export function statusFor(mode: ControlMode, assignedOperatorName?: string): StatusInfo {
  if (mode === "ai") return { label: "AI отвечает", color: "var(--ai)", bg: "var(--ai-bg)", border: "var(--ai-border)", dot: "var(--ai)" };
  if (mode === "human") return { label: "Вы ведёте диалог", color: "var(--primary-text)", bg: "var(--primary-bg)", border: "var(--primary-border)", dot: "var(--primary)" };
  if (mode === "assigned") return { label: assignedOperatorName ? `Ведёт ${assignedOperatorName}` : "Ведёт другой оператор", color: "var(--n-3)", bg: "var(--n-10)", border: "var(--n-6)", dot: "var(--n-4)" };
  if (mode === "closed") return { label: "Диалог закрыт", color: "var(--n-3)", bg: "var(--n-9)", border: "var(--n-6)", dot: "var(--n-5)" };
  return { label: "Ждёт оператора", color: "var(--warning-text)", bg: "var(--warning-bg)", border: "var(--warning-border)", dot: "var(--warning)" };
}

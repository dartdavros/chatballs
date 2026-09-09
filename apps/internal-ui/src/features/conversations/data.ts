import type { ControlMode, DialogMode, StatusInfo } from "./types";
import { t } from "../../i18n";

export const modeDots: Record<DialogMode, string> = {
  wait: "var(--warning)",
  ai: "var(--ai)",
  operator: "var(--primary)",
  closed: "var(--n-5)",
};

export function statusFor(mode: ControlMode, assignedOperatorName?: string): StatusInfo {
  if (mode === "ai") return { label: t("conversations.ai_replying"), color: "var(--ai)", bg: "var(--ai-bg)", border: "var(--ai-border)", dot: "var(--ai)" };
  if (mode === "human") return { label: t("conversations.handling"), color: "var(--primary-text)", bg: "var(--primary-bg)", border: "var(--primary-border)", dot: "var(--primary)" };
  if (mode === "assigned") return { label: assignedOperatorName ? t("conversations.handled_by_short", { name: assignedOperatorName }) : t("conversations.another_operator_handling"), color: "var(--n-3)", bg: "var(--n-10)", border: "var(--n-6)", dot: "var(--n-4)" };
  if (mode === "closed") return { label: t("conversations.conversation_closed"), color: "var(--n-3)", bg: "var(--n-9)", border: "var(--n-6)", dot: "var(--n-5)" };
  return { label: t("conversations.waiting_person"), color: "var(--warning-text)", bg: "var(--warning-bg)", border: "var(--warning-border)", dot: "var(--warning)" };
}

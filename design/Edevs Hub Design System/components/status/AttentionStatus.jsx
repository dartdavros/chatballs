import React from "react";

const TONE = {
  ok: { dot: "#52c41a", color: "var(--success-text)", bg: "var(--success-bg)", border: "var(--success-border)", label: "Нормально" },
  attention: { dot: "#faad14", color: "var(--warning-text)", bg: "var(--warning-bg)", border: "var(--warning-border)", label: "Требует внимания" },
  critical: { dot: "#ff4d4f", color: "var(--error-text)", bg: "var(--error-bg)", border: "var(--error-border)", label: "Критично" },
};

/* AttentionStatus — the company/department health chip (ADR-HUB-0013 local component).
   Always pairs a colored dot with a text label so color is never the only signal. */
export function AttentionStatus(props) {
  const t = TONE[props.level ?? "ok"];
  return React.createElement(
    "span",
    {
      style: {
        display: "inline-flex",
        alignItems: "center",
        gap: 7,
        padding: "3px 11px",
        borderRadius: "var(--radius-pill)",
        background: t.bg,
        border: `1px solid ${t.border}`,
      },
    },
    React.createElement("span", { style: { width: 7, height: 7, borderRadius: "50%", background: t.dot, flex: "none" } }),
    React.createElement("span", { style: { fontSize: 12.5, fontWeight: 600, color: t.color } }, props.label ?? t.label)
  );
}

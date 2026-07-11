import React from "react";

const TONES = {
  neutral: { bg: "var(--n-9)", color: "var(--text-secondary)", border: "transparent" },
  primary: { bg: "var(--primary-bg)", color: "#0958d9", border: "transparent" },
  success: { bg: "var(--success-bg)", color: "var(--success-text)", border: "var(--success-border)" },
  warning: { bg: "var(--warning-bg)", color: "var(--warning-text)", border: "var(--warning-border)" },
  error: { bg: "var(--error-bg)", color: "var(--error-text)", border: "var(--error-border)" },
  ai: { bg: "var(--ai-bg)", color: "var(--ai)", border: "transparent" },
};

export function Tag(props) {
  const t = TONES[props.tone ?? "neutral"];
  return React.createElement(
    "span",
    {
      style: {
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: props.pill ? "3px 10px" : "2px 8px",
        borderRadius: props.pill ? "var(--radius-pill)" : "var(--radius-xs)",
        background: t.bg,
        border: t.border !== "transparent" ? `1px solid ${t.border}` : "none",
        fontSize: props.pill ? 12 : 11,
        fontWeight: props.pill ? 600 : 500,
        color: t.color,
        whiteSpace: "nowrap",
      },
    },
    props.dot ? React.createElement("span", { style: { width: 6, height: 6, borderRadius: "50%", background: props.dotColor ?? t.color, flex: "none" } }) : null,
    props.children
  );
}

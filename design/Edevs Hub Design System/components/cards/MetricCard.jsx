import React from "react";

/* MetricCard — a single KPI cell: value + label only, per ADR-HUB-0013
   ("карточки метрик должны содержать только показатель, контекст, изменение и состояние"). */
export function MetricCard(props) {
  return React.createElement(
    "div",
    { style: { background: "var(--surface-card)", padding: "13px 15px" } },
    React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 5, marginBottom: 7 } },
      props.dotColor ? React.createElement("span", { style: { width: 7, height: 7, borderRadius: "50%", background: props.dotColor } }) : null,
      React.createElement("span", { style: { fontSize: 12, color: "var(--text-tertiary)" } }, props.label)
    ),
    React.createElement("div", { style: { fontSize: 23, fontWeight: 700, color: props.valueColor ?? "var(--text-body)", lineHeight: 1 } }, props.value)
  );
}

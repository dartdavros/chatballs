import React from "react";

const STATUS = {
  connected: { dot: "#52c41a", label: "Подключено", color: "var(--success-text)" },
  degraded: { dot: "#faad14", label: "Деградация", color: "var(--warning-text)" },
  error: { dot: "#ff4d4f", label: "Ошибка", color: "var(--error-text)" },
};

/* IntegrationHealthCard — one row per external integration (payments, AI
   provider, channels, fulfillment) inside the Command Center right rail. */
export function IntegrationHealthCard(props) {
  const s = STATUS[props.status ?? "connected"];
  return React.createElement(
    "div",
    { style: { display: "flex", alignItems: "center", gap: 11, padding: "10px 18px", borderTop: "1px solid var(--n-9)" } },
    React.createElement("span", { style: { width: 8, height: 8, borderRadius: "50%", background: s.dot, flex: "none" } }),
    React.createElement(
      "span",
      { style: { flex: 1, minWidth: 0 } },
      React.createElement("span", { style: { display: "block", fontSize: 13, fontWeight: 500, color: "var(--text-body)", lineHeight: 1.25 } }, props.name),
      React.createElement("span", { style: { display: "block", fontSize: 11, color: "var(--text-disabled)" } }, props.group)
    ),
    React.createElement("span", { style: { fontSize: 12, fontWeight: 500, color: s.color, flex: "none" } }, s.label)
  );
}

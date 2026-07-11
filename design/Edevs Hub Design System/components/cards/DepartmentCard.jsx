import React from "react";
import { AttentionStatus } from "../status/AttentionStatus.jsx";
import { Button } from "../core/Button.jsx";
import { Icon } from "../core/Icon.jsx";

/* DepartmentCard — the Command Center's per-department summary
   (ADR-HUB-0013 local component). */
export function DepartmentCard(props) {
  return React.createElement(
    "div",
    { style: { background: "var(--surface-card)", border: "1px solid var(--n-8)", borderRadius: "var(--radius-2xl)", padding: "20px 22px", boxShadow: "var(--shadow-sm)" } },
    React.createElement(
      "div",
      { style: { display: "flex", alignItems: "flex-start", gap: 14 } },
      React.createElement(
        "div",
        { style: { width: 46, height: 46, borderRadius: 11, background: "var(--primary-bg)", display: "flex", alignItems: "center", justifyContent: "center", flex: "none" } },
        React.createElement(Icon, { name: props.icon ?? "departments", size: 23, color: "var(--primary)" })
      ),
      React.createElement(
        "div",
        { style: { flex: 1, minWidth: 0 } },
        React.createElement(
          "div",
          { style: { display: "flex", alignItems: "center", gap: 10 } },
          React.createElement("h3", { style: { margin: 0, fontSize: 18, fontWeight: 700, color: "var(--text-heading)" } }, props.name),
          React.createElement(AttentionStatus, { level: props.level })
        ),
        React.createElement("div", { style: { marginTop: 4, fontSize: 12.5, color: "var(--text-tertiary)" } }, props.meta)
      ),
      React.createElement(Button, { variant: "primary", onClick: props.onOpen }, props.openLabel ?? "Открыть отдел", React.createElement(Icon, { name: "arrowRight", size: 16 }))
    ),
    props.summary
      ? React.createElement("div", { style: { margin: "16px 0 0", padding: "10px 14px", background: "var(--surface-sunken)", borderRadius: "var(--radius-md)", fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.5 } }, props.summary)
      : null,
    props.children
  );
}

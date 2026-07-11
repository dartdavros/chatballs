import React from "react";
import { Tag } from "../core/Tag.jsx";

/* ProductAIReleaseCard — a snapshot of one AI knowledge/prompt release for a
   product (e.g. Foxray, FirePage) inside the AI section. */
export function ProductAIReleaseCard(props) {
  return React.createElement(
    "div",
    { style: { background: "var(--surface-card)", border: "1px solid var(--n-8)", borderRadius: "var(--radius-2xl)", padding: "16px 18px", boxShadow: "var(--shadow-sm)" } },
    React.createElement(
      "div",
      { style: { display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 } },
      React.createElement(
        "div",
        { style: { display: "flex", alignItems: "center", gap: 10 } },
        React.createElement("div", { style: { width: 34, height: 34, borderRadius: 9, background: props.iconBg ?? "var(--ai-bg)", color: props.iconColor ?? "var(--ai)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, fontWeight: 700, flex: "none" } }, props.productInitial),
        React.createElement(
          "div",
          null,
          React.createElement("div", { style: { fontSize: 14.5, fontWeight: 700, color: "var(--text-heading)" } }, props.productName),
          React.createElement("div", { style: { fontSize: 11, color: "var(--text-disabled)", fontFamily: "var(--font-mono)" } }, props.releaseId)
        )
      ),
      React.createElement(Tag, { pill: true, tone: props.live ? "success" : "neutral", dot: true }, props.live ? "Активен" : "Черновик")
    ),
    React.createElement(
      "div",
      { style: { display: "flex", gap: 1, background: "var(--n-8)", border: "1px solid var(--n-8)", borderRadius: "var(--radius-lg)", overflow: "hidden" } },
      (props.stats ?? []).map((s, i) =>
        React.createElement(
          "div",
          { key: i, style: { flex: 1, background: "#fff", padding: "9px 11px" } },
          React.createElement("div", { style: { fontSize: 11, color: "var(--text-tertiary)", marginBottom: 3 } }, s.label),
          React.createElement("div", { style: { fontSize: 14, fontWeight: 600, color: "var(--text-body)" } }, s.value)
        )
      )
    )
  );
}

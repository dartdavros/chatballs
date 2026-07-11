import React from "react";

const TONE = { done: "#3f8f3f", active: "var(--primary)", pending: "var(--n-6)" };

/* CommerceStatusTimeline — separates "payment confirmed" from "product
   delivered" as distinct steps (SPEC-HUB-0007: payment and delivery states
   must never be conflated). */
export function CommerceStatusTimeline(props) {
  return React.createElement(
    "div",
    { style: { display: "flex", flexDirection: "column", gap: 11 } },
    (props.steps ?? []).map((s, i) =>
      React.createElement(
        "div",
        { key: i, style: { display: "flex", alignItems: "center", gap: 11 } },
        s.state === "done"
          ? React.createElement(
              "div",
              { style: { width: 22, height: 22, borderRadius: "50%", background: "var(--success-bg-strong)", display: "flex", alignItems: "center", justifyContent: "center", flex: "none" } },
              React.createElement("svg", { viewBox: "0 0 24 24", width: 13, height: 13, fill: "none", stroke: TONE.done, strokeWidth: 2.6, strokeLinecap: "round", strokeLinejoin: "round" }, React.createElement("path", { d: "M20 6 9 17l-5-5" }))
            )
          : s.state === "active"
          ? React.createElement("div", { style: { width: 22, height: 22, borderRadius: "50%", border: `2px solid ${TONE.active}`, display: "flex", alignItems: "center", justifyContent: "center", flex: "none", animation: "hub-pulse 1.6s ease-in-out infinite" } },
              React.createElement("span", { style: { width: 7, height: 7, borderRadius: "50%", background: TONE.active } }))
          : React.createElement("div", { style: { width: 22, height: 22, borderRadius: "50%", border: `2px solid ${TONE.pending}`, flex: "none" } }),
        React.createElement("span", { style: { fontSize: 12.5, color: s.state === "active" ? "var(--text-body)" : "var(--text-secondary)", fontWeight: s.state === "active" ? 600 : 400 } }, s.label)
      )
    )
  );
}

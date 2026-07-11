import React from "react";

/* ActorBadge — distinguishes an AI participant from a human operator in a
   conversation timeline (ADR-HUB-0013: "ai"/"human" semantic tokens). */
export function ActorBadge(props) {
  const isAI = props.actor === "ai";
  if (isAI) {
    return React.createElement(
      "div",
      { style: { width: 28, height: 28, borderRadius: "50%", background: "#eef0f2", border: "1px solid #e3e6ea", display: "flex", alignItems: "center", justifyContent: "center", flex: "none" } },
      React.createElement(
        "svg",
        { viewBox: "0 0 24 24", width: 15, height: 15, fill: "none", stroke: "#8c8c8c", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round" },
        React.createElement("circle", { cx: 12, cy: 8, r: 3.2 }),
        React.createElement("path", { d: "M5.5 20a6.5 6.5 0 0 1 13 0" })
      )
    );
  }
  return React.createElement(
    "div",
    { style: { width: 28, height: 28, borderRadius: "50%", background: props.color ?? "var(--primary)", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 600, flex: "none" } },
    props.initials
  );
}

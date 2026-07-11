import React from "react";

export function Checkbox(props) {
  const on = !!props.checked;
  return React.createElement(
    "button",
    {
      type: "button",
      onClick: props.onChange,
      style: { display: "flex", alignItems: "flex-start", gap: 10, background: "none", border: "none", padding: 0, cursor: "pointer", textAlign: "left" },
    },
    React.createElement(
      "span",
      {
        style: {
          width: props.size === "sm" ? 17 : 20,
          height: props.size === "sm" ? 17 : 20,
          borderRadius: props.size === "sm" ? 5 : 6,
          flex: "none",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          border: on ? "none" : "1.5px solid var(--n-6)",
          background: on ? "var(--primary)" : "var(--surface-card)",
          marginTop: props.label ? 1 : 0,
        },
      },
      on
        ? React.createElement(
            "svg",
            { viewBox: "0 0 24 24", width: props.size === "sm" ? 12 : 13, height: props.size === "sm" ? 12 : 13, fill: "none", stroke: "#fff", strokeWidth: 3, strokeLinecap: "round", strokeLinejoin: "round" },
            React.createElement("path", { d: "M20 6 9 17l-5-5" })
          )
        : null
    ),
    props.label ? React.createElement("span", { style: { fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.45 } }, props.label) : null
  );
}

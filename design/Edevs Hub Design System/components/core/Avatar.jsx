import React from "react";

export function Avatar(props) {
  const size = props.size ?? 32;
  return React.createElement(
    "div",
    {
      style: {
        width: size,
        height: size,
        borderRadius: "50%",
        background: props.color ?? "var(--primary)",
        color: "#fff",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: Math.round(size * 0.38),
        fontWeight: 600,
        flex: "none",
      },
    },
    props.initials
  );
}

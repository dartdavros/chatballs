import React from "react";

export function IconButton(props) {
  const size = props.size ?? 36;
  const [hover, setHover] = React.useState(false);
  return React.createElement(
    "button",
    {
      style: {
        position: "relative",
        width: size,
        height: size,
        borderRadius: "var(--radius-md)",
        border: props.bare ? "none" : "1px solid var(--n-8)",
        background: hover ? "var(--n-9)" : "var(--surface-card)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        cursor: "pointer",
        color: hover ? "var(--text-body)" : "var(--text-secondary)",
        flex: "none",
      },
      onClick: props.onClick,
      onMouseEnter: () => setHover(true),
      onMouseLeave: () => setHover(false),
      "aria-label": props.label,
      title: props.label,
    },
    props.children,
    props.badge
      ? React.createElement(
          "span",
          {
            style: {
              position: "absolute",
              top: 6,
              right: 7,
              minWidth: 15,
              height: 15,
              padding: "0 4px",
              borderRadius: 8,
              background: "var(--error)",
              color: "#fff",
              fontSize: 10,
              fontWeight: 600,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              border: "1.5px solid var(--surface-card)",
            },
          },
          props.badge
        )
      : null
  );
}

import React from "react";

export function Input(props) {
  const [focused, setFocused] = React.useState(false);
  const hasError = !!props.error;
  const borderColor = hasError ? "var(--error-border)" : focused ? "var(--primary)" : "var(--border-input)";
  return React.createElement(
    "div",
    { style: { display: "flex", flexDirection: "column", gap: 5, width: props.fullWidth === false ? "auto" : "100%" } },
    props.label
      ? React.createElement(
          "label",
          { style: { fontSize: 12.5, fontWeight: 500, color: "var(--text-secondary)" } },
          props.label,
          props.required ? React.createElement("span", { style: { color: "var(--error-text)" } }, " *") : null
        )
      : null,
    React.createElement(
      "div",
      {
        style: {
          display: "flex",
          alignItems: "center",
          gap: 9,
          height: "var(--h-control-lg)",
          padding: "0 13px",
          border: `1px solid ${borderColor}`,
          borderRadius: "var(--radius-lg)",
          background: props.disabled ? "var(--n-9)" : "var(--surface-card)",
        },
      },
      props.icon,
      React.createElement("input", {
        type: props.type ?? "text",
        value: props.value,
        onChange: props.onChange,
        placeholder: props.placeholder,
        disabled: props.disabled,
        onFocus: () => setFocused(true),
        onBlur: () => setFocused(false),
        style: {
          flex: 1,
          border: "none",
          outline: "none",
          background: "transparent",
          fontSize: 14,
          color: "var(--text-body)",
          fontFamily: "var(--font-sans)",
          width: "100%",
        },
      }),
      props.suffix
    ),
    props.hint ? React.createElement("div", { style: { fontSize: 11, color: hasError ? "var(--error-text)" : "var(--text-tertiary)" } }, props.hint) : null
  );
}

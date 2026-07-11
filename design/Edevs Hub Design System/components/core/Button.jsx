import React from "react";

const SIZES = {
  sm: { h: 30, padX: 12, font: "13px" },
  md: { h: 36, padX: 14, font: "13px" },
  lg: { h: 44, padX: 22, font: "14.5px" },
};

export function Button(props) {
  const variant = props.variant ?? "primary";
  const size = props.size ?? "md";
  const disabled = !!props.disabled;
  const s = SIZES[size] ?? SIZES.md;
  const [hover, setHover] = React.useState(false);

  const base = {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 7,
    height: s.h,
    padding: `0 ${s.padX}px`,
    borderRadius: "var(--radius-lg)",
    fontSize: s.font,
    fontWeight: 600,
    fontFamily: "var(--font-sans)",
    cursor: disabled ? "not-allowed" : "pointer",
    border: "1px solid transparent",
    transition: "background var(--duration-fast), border-color var(--duration-fast), color var(--duration-fast)",
    opacity: disabled ? 0.55 : 1,
    whiteSpace: "nowrap",
  };

  const byVariant = {
    primary: {
      background: hover && !disabled ? "var(--primary-hover)" : "var(--primary)",
      color: "var(--text-inverse)",
      boxShadow: "var(--shadow-primary)",
    },
    secondary: {
      background: "var(--surface-card)",
      color: hover && !disabled ? "var(--primary)" : "var(--text-body)",
      borderColor: hover && !disabled ? "var(--primary)" : "var(--n-6)",
    },
    ghost: {
      background: hover && !disabled ? "var(--n-9)" : "transparent",
      color: "var(--text-body)",
    },
    danger: {
      background: hover && !disabled ? "#d9363e" : "var(--error)",
      color: "var(--text-inverse)",
    },
  };

  return React.createElement(
    "button",
    {
      style: { ...base, ...byVariant[variant] },
      disabled,
      onClick: props.onClick,
      onMouseEnter: () => setHover(true),
      onMouseLeave: () => setHover(false),
      type: props.type ?? "button",
    },
    props.children
  );
}

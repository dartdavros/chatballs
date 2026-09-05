import type { ReactNode } from "react";

import { Icon } from "../../shared/icons";

export function AuthField({
  children,
  error = false,
  icon,
  onChange,
  placeholder,
  type = "text",
  value,
  variant = "",
}: {
  children?: ReactNode;
  error?: boolean;
  icon: "lock" | "mail" | "building" | "user";
  onChange: (value: string) => void;
  placeholder: string;
  type?: "password" | "text";
  value: string;
  variant?: string;
}) {
  const className = ["auth-field", variant, error ? "is-error" : ""].filter(Boolean).join(" ");
  return (
    <div className={className}>
      <Icon name={icon} size={16} />
      <input type={type} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} />
      {children}
    </div>
  );
}

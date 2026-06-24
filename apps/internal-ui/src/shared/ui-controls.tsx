import type { AnchorHTMLAttributes, ButtonHTMLAttributes, ReactNode } from "react";

import { Icon } from "./icons";

type IconName = Parameters<typeof Icon>[0]["name"];

type ButtonVariant = "action" | "danger-outline" | "primary" | "secondary";

const buttonVariantClass: Record<ButtonVariant, string> = {
  action: "ui-action-button",
  "danger-outline": "danger-outline",
  primary: "primary-button",
  secondary: "secondary-button",
};

type ActionButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  icon?: IconName;
  iconSize?: number;
};

type ButtonProps = ActionButtonProps & {
  variant: ButtonVariant;
};

type SearchInputProps = {
  className?: string;
  placeholder: string;
  value?: string;
  onChange?: (value: string) => void;
};

type UnderlineTabsProps<T extends string> = {
  className?: string;
  items: Array<{ key: T; label: string; count?: number; disabled?: boolean }>;
  value: T;
  onChange: (value: T) => void;
};

type ToneBadgeProps = {
  bg: string;
  children: ReactNode;
  className?: string;
  color: string;
};

type TablePaginationProps = {
  className?: string;
  pageSizeLabel: string;
  pages: Array<number | "ellipsis">;
  shown: number;
  total: number;
};

export function Button({ children, className = "", icon, iconSize = 15, type = "button", variant, ...buttonProps }: ButtonProps) {
  return (
    <button className={`${buttonVariantClass[variant]} ${className}`.trim()} type={type} {...buttonProps}>
      {icon && <Icon name={icon} size={iconSize} />}
      {children}
    </button>
  );
}

export function ActionButton(props: ActionButtonProps) {
  return <Button {...props} variant="action" />;
}

export function SearchInput({ className = "", placeholder, value, onChange }: SearchInputProps) {
  return (
    <label className={`ui-search-input ${className}`.trim()}>
      <Icon name="search" size={15} />
      <input value={value} onChange={(event) => onChange?.(event.target.value)} placeholder={placeholder} />
    </label>
  );
}

export function UnderlineTabs<T extends string>({ className = "", items, value, onChange }: UnderlineTabsProps<T>) {
  return (
    <div className={`ui-underline-tabs ${className}`.trim()}>
      {items.map((item) => (
        <button className={value === item.key ? "active" : ""} type="button" disabled={item.disabled} onClick={() => onChange(item.key)} key={item.key}>
          {item.label}
          {item.count !== undefined && <span>{item.count}</span>}
        </button>
      ))}
    </div>
  );
}

export function ToneBadge({ bg, className = "", color, children }: ToneBadgeProps) {
  return <span className={`ui-tone-badge ${className}`.trim()} style={{ background: bg, color }}>{children}</span>;
}

export function MonoLink({ children, className = "", href = "#", onClick, ...linkProps }: AnchorHTMLAttributes<HTMLAnchorElement> & { children: string }) {
  return (
    <a
      className={`ui-mono-link ${className}`.trim()}
      href={href}
      onClick={(event) => {
        if (href === "#") event.preventDefault();
        onClick?.(event);
      }}
      {...linkProps}
    >
      {children}
    </a>
  );
}

export function TablePagination({ className = "", pageSizeLabel, pages, shown, total }: TablePaginationProps) {
  return (
    <div className={`ui-table-pagination ${className}`.trim()}>
      <div>Показано {shown} из {total}</div>
      <div>
        <button type="button" disabled>‹</button>
        {pages.map((page, index) => page === "ellipsis" ? <span key={`ellipsis-${index}`}>…</span> : <button className={page === 1 ? "active" : ""} type="button" key={page}>{page}</button>)}
        <button type="button">›</button>
        <i />
        <em>{pageSizeLabel}</em>
      </div>
    </div>
  );
}

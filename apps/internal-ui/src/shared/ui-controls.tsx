import type { ButtonHTMLAttributes, ReactNode } from "react";

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
  currentPage?: number;
  onPageChange?: (page: number) => void;
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

/** Кнопка-иконка: подпись обязательна и уходит в aria-label и title. */
export function IconButton({ icon, iconSize = 16, label, bare = false, className = "", ...buttonProps }: Omit<ActionButtonProps, "icon"> & { icon: IconName; label: string; bare?: boolean }) {
  return (
    <button className={`ui-icon-button ${bare ? "is-bare" : ""} ${className}`.trim()} type="button" aria-label={label} title={label} {...buttonProps}>
      <Icon name={icon} size={iconSize} />
    </button>
  );
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

export function TablePagination({ className = "", currentPage = 1, onPageChange, pageSizeLabel, pages, shown, total }: TablePaginationProps) {
  const numericPages = pages.filter((page): page is number => page !== "ellipsis");
  const lastPage = Math.max(...numericPages, 1);
  return (
    <div className={`ui-table-pagination ${className}`.trim()}>
      <div>Показано {shown} из {total}</div>
      <div>
        <button type="button" disabled={!onPageChange || currentPage <= 1} onClick={() => onPageChange?.(currentPage - 1)}>‹</button>
        {pages.map((page, index) => page === "ellipsis" ? <span key={`ellipsis-${index}`}>…</span> : <button className={page === currentPage ? "active" : ""} type="button" disabled={!onPageChange} onClick={() => onPageChange?.(page)} key={page}>{page}</button>)}
        <button type="button" disabled={!onPageChange || currentPage >= lastPage} onClick={() => onPageChange?.(currentPage + 1)}>›</button>
        <i />
        <em>{pageSizeLabel}</em>
      </div>
    </div>
  );
}

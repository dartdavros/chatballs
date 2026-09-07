import { Dropdown } from "antd";
import { useEffect, useRef, useState, type ButtonHTMLAttributes, type ReactNode, type RefObject } from "react";

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
  inputRef?: RefObject<HTMLInputElement | null>;
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

/** Кнопка «копировать» рядом со значением (контекст-панель чата и карточка
 *  контакта): на 1.2 с превращается в галочку. */
export function CopyButton({ value, className = "", label }: { value: string; className?: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      className={`${className} ${copied ? "is-copied" : ""}`.trim()}
      aria-label="Скопировать"
      title={copied ? "Скопировано" : "Скопировать"}
      onClick={(event) => {
        event.stopPropagation();
        void navigator.clipboard?.writeText(value).then(() => {
          setCopied(true);
          window.setTimeout(() => setCopied(false), 1200);
        });
      }}
    >
      <Icon name={copied ? "check" : "copy"} size={13} strokeWidth={label ? 2 : 1.8} />
      {label && (copied ? "Скопировано" : label)}
    </button>
  );
}

/** «Назад» над карточкой сущности: шеврон и название раздела (дизайн-базлайн
 *  v2 — кадры K3 «Контакты», G3 «Агенты»). */
export function BackLink({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button className="ui-back-link" type="button" onClick={onClick}>
      <Icon name="chevronLeft" size={14} strokeWidth={2.2} />{label}
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

/** Поиск списка — один на всё приложение: иконка, поле, подсказка горячей
 *  клавиши. С `hotkey` клавиша ставит фокус в поле, если пользователь не пишет
 *  в другом поле и не открыл меню (SPEC-HUB-0031 §9). */
export function SearchInput({ className = "", placeholder, value, onChange, inputRef, hotkey }: SearchInputProps & { hotkey?: string }) {
  const ownRef = useRef<HTMLInputElement | null>(null);
  const field = inputRef ?? ownRef;

  useEffect(() => {
    if (!hotkey) return undefined;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key !== hotkey || event.metaKey || event.ctrlKey || event.altKey) return;
      const target = event.target;
      // Не перехватываем клавишу, когда человек пишет в другом поле или открыл меню.
      if (target instanceof Element && target.closest("input, textarea, [contenteditable], .ant-dropdown")) return;
      event.preventDefault();
      field.current?.focus();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [field, hotkey]);

  return (
    <label className={`ui-search-input ${className}`.trim()}>
      <Icon name="search" size={15} />
      <input ref={field} value={value} onChange={(event) => onChange?.(event.target.value)} placeholder={placeholder} />
      {hotkey && !value && <kbd>{hotkey}</kbd>}
    </label>
  );
}

export type FilterOption = { value: string; label: string; dot?: string };

/** Фильтр-селект списка — один на всё приложение: кнопка с текущим значением и
 *  шевроном, меню — общий `app-dropdown`. `multiple` включает галочки и счётчик
 *  выбранных (кадры K1 «Контакты», E1 «Сотрудники»). */
export function FilterDropdown({ caption, className = "", icon, label, options, selected, multiple = false, open, onOpenChange, onSelect }: {
  /** Приглушённая подпись перед значением: «Статус: Все» (кадры PT1/PT3). */
  caption?: string;
  className?: string;
  icon?: IconName;
  label: string;
  options: FilterOption[];
  selected: string[];
  multiple?: boolean;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelect: (value: string) => void;
}) {
  const items = options.map((option) => ({
    key: option.value,
    label: (
      <button
        type="button"
        onClick={(event) => {
          if (multiple) event.stopPropagation();
          onSelect(option.value);
        }}
      >
        {multiple && (
          <span className={`ui-filter-check ${selected.includes(option.value) ? "is-on" : ""}`}>
            {selected.includes(option.value) && <Icon name="check" size={12} />}
          </span>
        )}
        {option.dot && <i className="ui-filter-dot" style={{ background: option.dot }} />}
        {option.label}
      </button>
    ),
  }));
  const active = selected.length > 0;
  return (
    <Dropdown menu={{ items }} open={open} onOpenChange={onOpenChange} trigger={["click"]} overlayClassName="app-dropdown is-wide">
      <button className={`ui-filter-button ${active ? "is-active" : ""} ${className}`.trim()} type="button">
        {icon && <Icon name={icon} size={14} strokeWidth={2} />}
        {caption && <i className="ui-filter-caption">{caption}</i>}
        {label}
        {multiple && selected.length > 0 && <span>{selected.length}</span>}
        <Icon name="chevron" size={13} strokeWidth={2.2} />
      </button>
    </Dropdown>
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

/** Номера страниц с многоточиями: 1 … 4 5 6 … 20. Один расчёт на приложение —
 *  им живут пагинаторы контактов и журнала аудита. */
export function paginationItems(page: number, pageCount: number): Array<number | "ellipsis"> {
  if (pageCount <= 7) return Array.from({ length: pageCount }, (_, index) => index + 1);
  const pages = new Set([1, pageCount, page - 1, page, page + 1]);
  const visible = [...pages].filter((item) => item >= 1 && item <= pageCount).sort((a, b) => a - b);
  const result: Array<number | "ellipsis"> = [];
  visible.forEach((item, index) => {
    if (index > 0 && item - visible[index - 1] > 1) result.push("ellipsis");
    result.push(item);
  });
  return result;
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

import { Dropdown } from "antd";
import { useState, type ButtonHTMLAttributes, type CSSProperties, type ReactElement, type ReactNode } from "react";

import { Icon } from "./icons";
import { t } from "../i18n";

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
      aria-label={t("common.copy_clipboard")}
      title={copied ? t("common.copied") : t("common.copy_clipboard")}
      onClick={(event) => {
        event.stopPropagation();
        void navigator.clipboard?.writeText(value).then(() => {
          setCopied(true);
          window.setTimeout(() => setCopied(false), 1200);
        });
      }}
    >
      <Icon name={copied ? "check" : "copy"} size={13} strokeWidth={label ? 2 : 1.8} />
      {label && (copied ? t("common.copied") : label)}
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

export { SearchInput } from "./SearchInput";

/** `hint` — пояснение второй строкой под названием; у недоступного варианта
 *  (`disabled`) в нём пишут причину. */
export type SelectOption = { value: string; label: string; dot?: string; icon?: IconName; hint?: string; disabled?: boolean };

/** Совместимое имя: фильтры списков звали вариант `FilterOption`. */
export type FilterOption = SelectOption;

/** Выпадающий список приложения — один на все селекты: и на фильтры списков, и
 *  на поля форм. Своей разметки у него нет, только меню в общем `app-dropdown`
 *  и триггер, который передают снаружи: у фильтра это кнопка-пилюля, у поля
 *  формы — бокс на всю ширину. Галочки включает `multiple`. Нативных `<select>`
 *  в проекте нет — список вариантов всегда рисуем сами, иначе на месте меню
 *  оказывается список операционной системы. */
export function SelectMenu({ children, disabled = false, multiple = false, onOpenChange, onSelect, open, options, overlayClassName = "app-dropdown is-wide", overlayStyle, placement, selected }: {
  children: ReactElement;
  disabled?: boolean;
  multiple?: boolean;
  onOpenChange: (open: boolean) => void;
  onSelect: (value: string) => void;
  open: boolean;
  options: SelectOption[];
  overlayClassName?: string;
  overlayStyle?: CSSProperties;
  placement?: "bottomLeft" | "bottomRight";
  selected: string[];
}) {
  const items = options.map((option) => ({
    key: option.value,
    disabled: option.disabled,
    label: (
      <button
        className={!multiple && selected.includes(option.value) ? "is-selected" : ""}
        type="button"
        disabled={option.disabled}
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
        {option.icon && <Icon name={option.icon} size={14} strokeWidth={1.9} />}
        {option.hint ? <span>{option.label}<small>{option.hint}</small></span> : option.label}
      </button>
    ),
  }));
  return (
    <Dropdown
      menu={{ items }}
      open={disabled ? false : open}
      onOpenChange={onOpenChange}
      trigger={["click"]}
      disabled={disabled}
      overlayClassName={overlayClassName}
      overlayStyle={overlayStyle}
      placement={placement}
    >
      {children}
    </Dropdown>
  );
}

/** Фильтр-селект списка: кнопка с текущим значением и шевроном. `multiple`
 *  включает галочки и счётчик выбранных (кадры K1 «Контакты», E1 «Сотрудники»). */
export function FilterDropdown({ caption, className = "", icon, label, options, selected, multiple = false, open, onOpenChange, onSelect }: {
  /** Приглушённая подпись перед значением: «Статус: Все» (кадры PT1/PT3). */
  caption?: string;
  className?: string;
  icon?: IconName;
  label: string;
  options: SelectOption[];
  selected: string[];
  multiple?: boolean;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelect: (value: string) => void;
}) {
  const active = selected.length > 0;
  return (
    <SelectMenu multiple={multiple} onOpenChange={onOpenChange} onSelect={onSelect} open={open} options={options} selected={selected}>
      <button className={`ui-filter-button ${active ? "is-active" : ""} ${className}`.trim()} type="button">
        {icon && <Icon name={icon} size={14} strokeWidth={2} />}
        {caption && <i className="ui-filter-caption">{caption}</i>}
        <span className="ui-filter-label" title={label}>{label}</span>
        {multiple && selected.length > 0 && <span>{selected.length}</span>}
        <Icon name="chevron" size={13} strokeWidth={2.2} />
      </button>
    </SelectMenu>
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


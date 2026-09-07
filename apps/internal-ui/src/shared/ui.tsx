import type { ReactNode } from "react";

import type { Employee, Product, Role, SessionUser } from "../types";
import { FormField } from "./form-controls";
import { Icon, LogoSpinner } from "./icons";

type IconName = Parameters<typeof Icon>[0]["name"];
import { Button } from "./ui-controls";
import { initials, productAccent } from "./utils";

export function Avatar({ user, employee, background }: { user?: SessionUser; employee?: Employee; background?: string }) {
  const label = employee ? initials(employee.fullName, employee.email) : initials(user?.fullName ?? "", user?.email ?? "");
  const photo = employee ? employee.avatarUrl : user?.avatarUrl;
  // Фото сотрудника (дизайн-базлайн v2); без фото — инициалы на подложке:
  // по умолчанию акцент, в списке сотрудников — цвет из палитры (кадр E1).
  if (photo) return <span className="avatar has-photo"><img src={photo} alt="" /></span>;
  return <span className="avatar" style={background ? { background } : undefined}>{label}</span>;
}

export function PageHeader({ title, text, action }: { title: string; text?: ReactNode; action?: ReactNode }) {
  return (
    <div className="page-header">
      <div><h1>{title}</h1>{text && <p>{text}</p>}</div>
      {action}
    </div>
  );
}

export type StatusPillKey = "normal" | "active" | "published" | "blocked" | "disabled" | "invited" | "archived" | "draft" | "healthy" | "error" | "pending" | "unchecked";

export function StatusPill({ status, label: labelOverride }: { status: StatusPillKey; label?: string }) {
  const map = {
    normal: ["var(--success-bg)", "var(--success-border)", "var(--success-text)", "Работает"],
    active: ["transparent", "transparent", "var(--success-text)", "Активен"],
    published: ["var(--success-bg)", "var(--success-border)", "var(--success-text)", "Опубликован"],
    blocked: ["transparent", "transparent", "var(--error-text)", "Заблокирован"],
    disabled: ["transparent", "transparent", "var(--warning-text)", "Неактивен"],
    invited: ["transparent", "transparent", "var(--primary-text)", "Приглашён"],
    archived: ["var(--n-9)", "var(--n-7)", "var(--n-4)", "Архивный"],
    draft: ["var(--n-10)", "var(--n-7)", "var(--n-4)", "Черновик"],
    healthy: ["var(--success-bg)", "var(--success-border)", "var(--success-text)", "Работает"],
    error: ["var(--error-bg)", "var(--error-border)", "var(--error-text)", "Ошибка"],
    pending: ["var(--warning-bg)", "var(--warning-border)", "var(--warning-text)", "Проверяется"],
    unchecked: ["var(--n-10)", "var(--n-7)", "var(--n-4)", "Не проверялось"],
  } as const;
  const [bg, border, color, label] = map[status];
  const dotStyle = status === "archived"
    ? { background: "transparent", border: `1.5px solid ${color}` }
    : { background: color };
  return <span className={`status-pill ${status}`} style={{ background: bg, borderColor: border, color }}><span style={dotStyle} />{labelOverride ?? label}</span>;
}

const ROLE_LABELS: Record<Role, string> = {
  OWNER: "Владелец",
  ADMIN: "Администратор",
  EMPLOYEE: "Сотрудник",
};

export function roleLabel(role: Role): string {
  return ROLE_LABELS[role] ?? role;
}

export function RoleBadge({ role }: { role: Role }) {
  return <span className={`role-badge ${role.toLowerCase()}`}>{roleLabel(role)}</span>;
}

export function ProductTag({ product }: { product: Pick<Product, "code" | "name"> }) {
  const accent = productAccent(product.code);
  return (
    <span className="product-tag" style={{ background: accent.bg, color: accent.color }}>
      <i style={{ background: accent.color }} />
      {product.name}
    </span>
  );
}

export function ProductMark({ product }: { product: Pick<Product, "code" | "name"> }) {
  const accent = productAccent(product.code);
  return <span className="product-mark"><i style={{ background: accent.color }} />{product.name}</span>;
}

export function ContentState({ icon, tone = "primary", title, text, action, className = "" }: { icon: ReactNode; tone?: "primary" | "warning"; title: string; text: ReactNode; action?: ReactNode; className?: string }) {
  return (
    <div className={`content-state ${className}`.trim()}>
      <span className={`content-state-icon is-${tone}`}>{icon}</span>
      <strong>{title}</strong>
      <p>{text}</p>
      {action}
    </div>
  );
}

export function ReadOnlyField({ label, value, editable = false, mono = false, wide = false }: { label: string; value: string; editable?: boolean; mono?: boolean; wide?: boolean }) {
  return <FormField label={label} value={value} mono={mono} wide={wide} disabled={!editable} />;
}

export function PasswordField({ label, value = "", placeholder = "" }: { label: string; value?: string; placeholder?: string }) {
  return <FormField label={label} value={value} placeholder={placeholder} type="password" />;
}

/** Сегмент-переключатель. Третий и четвёртый элементы кортежа — иконка пункта
 *  и подсказка (кадр PT7: «Текст / Вместе / Просмотр»). */
export function Segmented<T extends string>({ className = "", value, setValue, items }: { className?: string; value: T; setValue: (value: T) => void; items: Array<[T, string] | [T, string, IconName, string]> }) {
  return (
    <div className={`segmented ${className}`.trim()}>
      {items.map(([key, label, icon, title]) => (
        <button className={value === key ? "active" : ""} key={key} title={title} type="button" onClick={() => setValue(key)}>
          {icon && <Icon name={icon} size={14} strokeWidth={1.9} />}
          {label}
        </button>
      ))}
    </div>
  );
}

export function EmptyState({ title }: { title: string }) {
  return <div className="empty-state"><strong>{title}</strong></div>;
}

export function LoadingState({ variant = "page" }: { variant?: "page" | "inline" }) {
  return <div className={`loading-state ${variant}`}><LogoSpinner size={variant === "inline" ? 22 : 32} /></div>;
}

export function LoadingScreen() {
  return <main className="state-screen"><div className="state-card"><LoadingState variant="inline" /></div></main>;
}

export function ErrorScreen({ retry }: { retry: () => void }) {
  return <main className="state-screen"><div className="state-card"><strong>Ошибка загрузки</strong><Button variant="primary" onClick={retry}>Повторить</Button></div></main>;
}

export function PermissionScreen({ onReturn }: { onReturn: () => void }) {
  return (
    <main className="state-screen">
      <div className="state-card">
        <strong>403 · Доступ запрещён</strong>
        <span>У вашей роли нет доступа к этому разделу.</span>
        <Button variant="primary" onClick={onReturn}>Вернуться</Button>
      </div>
    </main>
  );
}

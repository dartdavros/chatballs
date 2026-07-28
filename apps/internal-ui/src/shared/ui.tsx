import type { ReactNode } from "react";

import type { Employee, Product, Role, SessionUser } from "../types";
import { FormField } from "./form-controls";
import { Icon } from "./icons";
import { Button } from "./ui-controls";
import { initials, productAccent } from "./utils";

export function Avatar({ user, employee }: { user?: SessionUser; employee?: Employee }) {
  const label = employee ? initials(employee.fullName, employee.email) : initials(user?.fullName ?? "", user?.email ?? "");
  return <span className="avatar">{label}</span>;
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

export function StatusPill({ status }: { status: StatusPillKey }) {
  const map = {
    normal: ["#f6ffed", "#b7eb8f", "#389e0d", "Работает"],
    active: ["transparent", "transparent", "#389e0d", "Активен"],
    published: ["#f6ffed", "#b7eb8f", "#389e0d", "Опубликован"],
    blocked: ["transparent", "transparent", "#cf1322", "Заблокирован"],
    disabled: ["transparent", "transparent", "#d48806", "Неактивен"],
    invited: ["transparent", "transparent", "#0958d9", "Приглашён"],
    archived: ["#f5f5f5", "#e8e8e8", "#8c8c8c", "Архивный"],
    draft: ["#fafafa", "#e8e8e8", "#8c8c8c", "Черновик"],
    healthy: ["#f6ffed", "#b7eb8f", "#389e0d", "Работает"],
    error: ["#fff2f0", "#ffccc7", "#cf1322", "Ошибка"],
    pending: ["#fffbe6", "#ffe58f", "#d48806", "Проверяется"],
    unchecked: ["#fafafa", "#e8e8e8", "#8c8c8c", "Не проверялось"],
  } as const;
  const [bg, border, color, label] = map[status];
  const dotStyle = status === "archived"
    ? { background: "transparent", border: `1.5px solid ${color}` }
    : { background: color };
  return <span className={`status-pill ${status}`} style={{ background: bg, borderColor: border, color }}><span style={dotStyle} />{label}</span>;
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

export function Segmented<T extends string>({ value, setValue, items }: { value: T; setValue: (value: T) => void; items: Array<[T, string]> }) {
  return <div className="segmented">{items.map(([key, label]) => <button className={value === key ? "active" : ""} onClick={() => setValue(key)} key={key}>{label}</button>)}</div>;
}

export function EmptyState({ title }: { title: string }) {
  return <div className="empty-state"><strong>{title}</strong></div>;
}

export function LoadingState({ variant = "page" }: { variant?: "page" | "inline" }) {
  return <div className={`loading-state ${variant}`}><strong>Загрузка…</strong></div>;
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

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

export function StatusPill({ status }: { status: "normal" | "active" | "blocked" | "disabled" | "invited" }) {
  const map = {
    normal: ["#f6ffed", "#b7eb8f", "#389e0d", "NORMAL"],
    active: ["transparent", "transparent", "#389e0d", "Активен"],
    blocked: ["transparent", "transparent", "#cf1322", "Заблокирован"],
    disabled: ["transparent", "transparent", "#d48806", "Неактивен"],
    invited: ["transparent", "transparent", "#0958d9", "Приглашён"],
  } as const;
  const [bg, border, color, label] = map[status];
  return <span className="status-pill" style={{ background: bg, borderColor: border, color }}><span style={{ background: color }} />{label}</span>;
}

export function RoleBadge({ role }: { role: Role }) {
  return <span className={`role-badge ${role.toLowerCase()}`}>{role}</span>;
}

export function ProductTag({ product }: { product: Product }) {
  const accent = productAccent(product.code);
  return <span style={{ background: accent.bg, color: accent.color }}>{product.name}</span>;
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

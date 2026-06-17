import { ConfigProvider } from "antd";
import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";

import { edevsHubTheme } from "@edevs/ui";

const API_BASE = "http://localhost:8010";

type Role = "OWNER" | "OPERATOR";
type ProductStatus = "ACTIVE" | "DISABLED";

type SessionUser = {
  id: number;
  email: string;
  fullName: string;
  role: Role;
  organization: string;
  organizationName: string;
  department: string | null;
  mustChangePassword: boolean;
  totpRequired: boolean;
  totpEnabled: boolean;
};

type AuthChallenge = {
  email: string;
  fullName: string;
  role: Role;
};

type LoginPayload =
  | { authenticated: true; user: SessionUser }
  | { authenticated: false; totpRequired: true; totpEnabled: true; challenge: AuthChallenge };

type Employee = {
  id: number;
  email: string;
  fullName: string;
  role: Role;
  department: string | null;
  isActive: boolean;
  isBlocked: boolean;
  mustChangePassword: boolean;
  totpRequired: boolean;
  totpEnabled: boolean;
};

type Department = {
  id: number;
  code: string;
  name: string;
  status: string;
  memberCount: number;
  operatorCount: number;
  activeOperatorCount: number;
  products: Array<{ code: string; name: string }>;
};

type Product = {
  id: number;
  code: string;
  name: string;
  status: ProductStatus;
  siteUrl: string;
  createdAt: string;
};

type RouteKey = "command" | "departments" | "employees" | "products" | "profile";

type AppData = {
  employees: Employee[];
  departments: Department[];
  products: Product[];
};

const routes: Record<RouteKey, string> = {
  command: "Командный центр",
  departments: "Отделы",
  employees: "Сотрудники",
  products: "Продукты",
  profile: "Профиль",
};

function getCookie(name: string): string {
  const cookie = document.cookie
    .split("; ")
    .find((item) => item.startsWith(`${name}=`));
  return cookie ? decodeURIComponent(cookie.split("=")[1]) : "";
}

async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = init.method ?? "GET";
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (method !== "GET") {
    headers.set("Content-Type", "application/json");
    headers.set("X-CSRFToken", getCookie("csrftoken"));
  }
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: "include",
    headers,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Ошибка запроса" }));
    throw new Error(payload.detail ?? "Ошибка запроса");
  }
  return response.json() as Promise<T>;
}

function initials(name: string, email: string): string {
  const source = name.trim() || email.split("@")[0] || "EH";
  const parts = source.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  return source.slice(0, 2).toUpperCase();
}

function productAccent(code: string): { bg: string; color: string } {
  if (code === "foxray") return { bg: "#f9f0ff", color: "#722ed1" };
  return { bg: "#e6f4ff", color: "#0958d9" };
}

function PulseIcon() {
  return (
    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 12h4l2 6 4-14 2 8h6" />
    </svg>
  );
}

function ShieldIcon() {
  return (
    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
      <path d="m9 12 2 2 4-5" />
    </svg>
  );
}

function Icon({ name, size = 17 }: { name: "grid" | "building" | "team" | "box" | "robot" | "plug" | "settings" | "bell" | "chevron" | "plus" | "arrow" | "lock" | "mail" | "eye" | "eyeOff" | "logout" | "user" | "refresh" | "warning" | "bolt" | "shop" | "search" | "more" | "external" | "key" | "pause" | "percent"; size?: number }) {
  const common = { width: size, height: size, fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round" } as const;
  const paths: Record<typeof name, ReactNode> = {
    grid: <><rect x="3" y="3" width="7" height="9" rx="1.4" /><rect x="14" y="3" width="7" height="5" rx="1.4" /><rect x="14" y="12" width="7" height="9" rx="1.4" /><rect x="3" y="16" width="7" height="5" rx="1.4" /></>,
    building: <><path d="M3 21h18" /><path d="M5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16" /><path d="M9 8h1.5M13.5 8H15M9 12h1.5M13.5 12H15M9 16h1.5M13.5 16H15" /></>,
    team: <><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M22 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></>,
    box: <><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z" /><path d="m3.3 7 8.7 5 8.7-5" /><path d="M12 22V12" /></>,
    robot: <><rect x="4" y="8" width="16" height="12" rx="2.5" /><path d="M12 8V4.5" /><circle cx="12" cy="3.5" r="1.2" /><circle cx="9" cy="13.5" r="1" /><circle cx="15" cy="13.5" r="1" /></>,
    plug: <><path d="M9 8V2.5M15 8V2.5M18 8v5.5a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4V8Z" /><path d="M12 17.5V22" /></>,
    settings: <><line x1="21" y1="6" x2="9" y2="6" /><line x1="3" y1="6" x2="5" y2="6" /><circle cx="7" cy="6" r="2" /><line x1="21" y1="12" x2="13" y2="12" /><line x1="3" y1="12" x2="9" y2="12" /><circle cx="11" cy="12" r="2" /><line x1="21" y1="18" x2="15" y2="18" /><line x1="3" y1="18" x2="11" y2="18" /><circle cx="13" cy="18" r="2" /></>,
    bell: <><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" /><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" /></>,
    chevron: <polyline points="6 9 12 15 18 9" />,
    plus: <><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></>,
    arrow: <><line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" /></>,
    refresh: <><path d="M3 12a9 9 0 0 1 15-6.7L21 8" /><path d="M21 3v5h-5" /><path d="M21 12a9 9 0 0 1-15 6.7L3 16" /><path d="M3 21v-5h5" /></>,
    warning: <><path d="m21.7 18-8-14a2 2 0 0 0-3.5 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3Z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></>,
    bolt: <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />,
    shop: <><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z" /><path d="M3 6h18" /><path d="M16 10a4 4 0 0 1-8 0" /></>,
    search: <><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></>,
    more: <><circle cx="12" cy="5" r="1" /><circle cx="12" cy="12" r="1" /><circle cx="12" cy="19" r="1" /></>,
    external: <><path d="M15 3h6v6" /><path d="M10 14 21 3" /><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" /></>,
    key: <><circle cx="7.5" cy="14.5" r="4.5" /><path d="m11 11 9-9" /><path d="m16 7 2 2" /><path d="m14 9 2 2" /></>,
    pause: <><rect x="6" y="4" width="4" height="16" rx="1" /><rect x="14" y="4" width="4" height="16" rx="1" /></>,
    percent: <><line x1="19" y1="5" x2="5" y2="19" /><circle cx="6.5" cy="6.5" r="2.5" /><circle cx="17.5" cy="17.5" r="2.5" /></>,
    lock: <><rect x="4" y="10" width="16" height="10" rx="2" /><path d="M8 10V7a4 4 0 0 1 8 0v3" /></>,
    mail: <><rect x="3" y="5" width="18" height="14" rx="2" /><path d="m3 7 9 6 9-6" /></>,
    eye: <><path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6Z" /><circle cx="12" cy="12" r="3" /></>,
    eyeOff: <><path d="m3 3 18 18" /><path d="M10.6 10.6a3 3 0 0 0 3.8 3.8" /><path d="M9.9 4.3A10.6 10.6 0 0 1 12 4c6.5 0 10 8 10 8a18 18 0 0 1-3.1 4.2" /><path d="M6.1 6.1C3.5 7.9 2 12 2 12s3.5 8 10 8c1.4 0 2.7-.3 3.9-.9" /></>,
    logout: <><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" /></>,
    user: <><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></>,
  };
  return <svg viewBox="0 0 24 24" {...common}>{paths[name]}</svg>;
}

function AuthFrame({ title, subtitle, logo, width = 400, children, note }: { title: string; subtitle: string; logo: "pulse" | "shield"; width?: number; children: ReactNode; note?: ReactNode }) {
  return (
    <main className="auth-screen">
      <div className="auth-box" style={{ width }}>
        <div className="auth-brand">
          <div className="auth-logo">{logo === "shield" ? <ShieldIcon /> : <PulseIcon />}</div>
          <h1>{title}</h1>
          <p>{subtitle}</p>
        </div>
        {children}
        {note && <div className="auth-note">{note}</div>}
      </div>
    </main>
  );
}

function AuthCodeCells({ value }: { value: string }) {
  const digits = value.padEnd(6, " ").slice(0, 6).split("");
  return <div className="auth-code-cells">{digits.map((digit, index) => <span className={digit.trim() ? "filled" : ""} key={index}>{digit}</span>)}</div>;
}

function AuthLogin({ onLogin, onTotpChallenge }: { onLogin: (user: SessionUser) => void; onTotpChallenge: (challenge: AuthChallenge) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [error, setError] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(false);
    try {
      const payload = await api<LoginPayload>("/api/v1/auth/login/", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      if (payload.authenticated) {
        onLogin(payload.user);
      } else {
        onTotpChallenge(payload.challenge);
      }
    } catch {
      setError(true);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthFrame title="Edevs Hub" subtitle="Вход во внутренний кабинет" logo="pulse" note="Доступ только для сотрудников Edevs · защищённое соединение">
      <form className="auth-card" onSubmit={submit}>
        {error && (
          <div className="auth-error">
            <span className="auth-error-dot">!</span>
            <span>Неверный email или пароль. Проверьте данные и попробуйте снова.</span>
          </div>
        )}
        <label className="field-label">Email</label>
        <div className={`auth-field ${error ? "is-error" : ""}`}>
          <Icon name="mail" size={16} />
          <input value={email} onChange={(event) => { setEmail(event.target.value); setError(false); }} placeholder="you@edevs.tech" />
        </div>
        <div className="password-row">
          <label className="field-label">Пароль</label>
          <a href="#" onClick={(event) => event.preventDefault()}>Восстановить доступ</a>
        </div>
        <div className={`auth-field auth-password ${error ? "is-error" : ""}`}>
          <Icon name="lock" size={16} />
          <input type={show ? "text" : "password"} value={password} onChange={(event) => { setPassword(event.target.value); setError(false); }} placeholder="Пароль" />
          <button type="button" onClick={() => setShow((value) => !value)} aria-label={show ? "Скрыть пароль" : "Показать пароль"}>
            <Icon name={show ? "eyeOff" : "eye"} size={17} />
          </button>
        </div>
        <button className="primary-button auth-submit" type="submit" disabled={submitting}>Войти<Icon name="arrow" size={16} /></button>
      </form>
    </AuthFrame>
  );
}

function passwordScore(password: string): number {
  if (!password) return 0;
  let score = password.length >= 10 ? 1 : 0;
  if (/\d/.test(password)) score += 1;
  if (/[A-Za-zА-Яа-я]/.test(password)) score += 1;
  if (/[^A-Za-zА-Яа-я0-9]/.test(password)) score += 1;
  return Math.min(score, 4);
}

function AuthChangePassword({ onChanged }: { user: SessionUser; onChanged: (user: SessionUser) => void }) {
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const score = passwordScore(password);
  const mismatch = confirm.length > 0 && password !== confirm;
  const valid = password.length >= 10 && /\d/.test(password) && /[A-Za-zА-Яа-я]/.test(password) && /[^A-Za-zА-Яа-я0-9]/.test(password) && !mismatch;
  const labels = ["Введите новый пароль", "Слабый пароль", "Средний пароль", "Хороший пароль", "Надёжный пароль"];

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!valid) return;
    setSubmitting(true);
    setError("");
    try {
      const payload = await api<{ authenticated: true; user: SessionUser }>("/api/v1/auth/change-temporary-password/", {
        method: "POST",
        body: JSON.stringify({ newPassword: password }),
      });
      onChanged(payload.user);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Не удалось сохранить пароль");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthFrame title="Смена временного пароля" subtitle="Вы вошли по временному паролю. Задайте постоянный пароль, чтобы продолжить." logo="shield" width={420}>
      <form className="auth-card" onSubmit={submit}>
        {error && <div className="auth-error"><span className="auth-error-dot">!</span><span>{error}</span></div>}
        <label className="field-label">Новый пароль</label>
        <div className="auth-field">
          <Icon name="lock" size={16} />
          <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Минимум 10 символов" />
        </div>
        <div className={`password-strength score-${score}`}>
          <div>{[0, 1, 2, 3].map((item) => <span className={item < score ? "active" : ""} key={item} />)}</div>
          <p>{labels[score]}</p>
        </div>
        <label className="field-label">Повторите пароль</label>
        <div className={`auth-field ${mismatch ? "is-error" : ""}`}>
          <Icon name="lock" size={16} />
          <input type="password" value={confirm} onChange={(event) => setConfirm(event.target.value)} placeholder="Повторите новый пароль" />
        </div>
        {mismatch && <div className="auth-inline-error">Пароли не совпадают</div>}
        <div className="password-requirements">
          <strong>ТРЕБОВАНИЯ К ПАРОЛЮ</strong>
          <span className={password.length >= 10 ? "done" : ""}>Не менее 10 символов</span>
          <span className={/\d/.test(password) ? "done" : ""}>Содержит цифру</span>
          <span className={/[A-Za-zА-Яа-я]/.test(password) && /[^A-Za-zА-Яа-я0-9]/.test(password) ? "done" : ""}>Буквы и спецсимвол</span>
        </div>
        <button className="primary-button auth-submit" type="submit" disabled={!valid || submitting}>Сохранить и войти</button>
      </form>
    </AuthFrame>
  );
}

function AuthTotpSetup({ user, onConfirmed }: { user: SessionUser; onConfirmed: (user: SessionUser) => void }) {
  const [secret, setSecret] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api<{ secret: string }>("/api/v1/auth/totp/setup/")
      .then((payload) => setSecret(payload.secret))
      .catch(() => setError(true));
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(false);
    try {
      const payload = await api<{ authenticated: true; user: SessionUser }>("/api/v1/auth/totp/confirm/", {
        method: "POST",
        body: JSON.stringify({ code }),
      });
      onConfirmed(payload.user);
    } catch {
      setError(true);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthFrame title="Двухфакторная проверка" subtitle="Введите 6-значный код из приложения-аутентификатора" logo="shield">
      <form className="auth-card" onSubmit={submit}>
        <div className="auth-account-strip">
          <span>{initials(user.fullName, user.email)}</span>
          <p>Вход как <strong>{user.email}</strong> · {user.role}</p>
        </div>
        {!user.totpEnabled && secret && <div className="auth-secret"><strong>Ключ настройки</strong><code>{secret}</code></div>}
        <AuthCodeCells value={code} />
        {error && <div className="auth-inline-error">Неверный код. Осталось попыток: 4</div>}
        <input className="auth-code-input" value={code} onChange={(event) => { setCode(event.target.value.replace(/\D/g, "").slice(0, 6)); setError(false); }} placeholder="Нажмите и введите код" inputMode="numeric" autoFocus />
        <button className="primary-button auth-submit" type="submit" disabled={code.length !== 6 || submitting}>Подтвердить</button>
        <div className="auth-hint">Код обновляется в приложении каждые 30 секунд</div>
        <button className="auth-link-button" type="button">Использовать резервный код</button>
      </form>
    </AuthFrame>
  );
}

function AuthTotpCode({ challenge, onVerified }: { challenge: AuthChallenge; onVerified: (user: SessionUser) => void }) {
  const [code, setCode] = useState("");
  const [error, setError] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(false);
    try {
      const payload = await api<{ authenticated: true; user: SessionUser }>("/api/v1/auth/totp/verify/", {
        method: "POST",
        body: JSON.stringify({ code }),
      });
      onVerified(payload.user);
    } catch {
      setError(true);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthFrame title="Подтверждение входа" subtitle={`Введите 6-значный код из приложения-аутентификатора для ${challenge.email}`} logo="shield">
      <form className="auth-card" onSubmit={submit}>
        {error && <div className="auth-error"><span className="auth-error-dot">!</span><span>Неверный код. Осталось попыток: 2</span></div>}
        <AuthCodeCells value={code} />
        <input className="auth-code-input spaced" value={code} onChange={(event) => { setCode(event.target.value.replace(/\D/g, "").slice(0, 6)); setError(false); }} placeholder="Введите код" inputMode="numeric" autoFocus />
        <button className="primary-button auth-submit" type="submit" disabled={code.length !== 6 || submitting}>Подтвердить</button>
        <div className="auth-hint">Код обновится через 0:24</div>
        <button className="auth-link-button" type="button">Нет доступа к коду? Связаться с поддержкой</button>
      </form>
    </AuthFrame>
  );
}

function Sidebar({ route, user, setRoute }: { route: RouteKey; user: SessionUser; setRoute: (route: RouteKey) => void }) {
  const nav = [
    { key: "command" as const, label: "Командный центр", icon: "grid" as const },
    { label: "КОМПАНИЯ", group: true },
    { key: "departments" as const, label: "Отделы", icon: "building" as const },
    { key: "employees" as const, label: "Сотрудники", icon: "team" as const },
    { key: "products" as const, label: "Продукты", icon: "box" as const },
    { label: "ПЛАТФОРМА", group: true },
    { label: "AI", icon: "robot" as const, disabled: true },
    { label: "Интеграции", icon: "plug" as const, disabled: true },
    { divider: true },
    { label: "Настройки", icon: "settings" as const, disabled: true },
  ];
  return (
    <aside className="hub-sidebar">
      <div className="hub-brand">
        <div className="hub-brand-mark"><PulseIcon /></div>
        <div><strong>Edevs Hub</strong><span>Уровень компании</span></div>
      </div>
      <nav className="hub-nav">
        {nav.map((item, index) => {
          if ("group" in item) return <div className="hub-nav-group" key={item.label}>{item.label}</div>;
          if ("divider" in item) return <div className="hub-nav-divider" key={index} />;
          const nextRoute = "key" in item ? item.key : null;
          const active = nextRoute === route;
          return (
            <button className={`hub-nav-item ${active ? "is-active" : ""}`} disabled={item.disabled} key={item.label} onClick={() => nextRoute && setRoute(nextRoute)}>
              {active && <span className="active-bar" />}
              <Icon name={item.icon} />
              {item.label}
            </button>
          );
        })}
      </nav>
      <button className={`profile-link ${route === "profile" ? "is-active" : ""}`} onClick={() => setRoute("profile")}>
        <Avatar user={user} />
        <span><strong>{user.fullName || user.email}</strong><small>{user.role}</small></span>
      </button>
    </aside>
  );
}

function Avatar({ user, employee }: { user?: SessionUser; employee?: Employee }) {
  const label = employee ? initials(employee.fullName, employee.email) : initials(user?.fullName ?? "", user?.email ?? "");
  return <span className="avatar">{label}</span>;
}

function TopBar({ route, user, onLogout }: { route: RouteKey; user: SessionUser; onLogout: () => void }) {
  const st = commandCenterModel("today").st;
  const isCommand = route === "command";
  return (
    <header className="hub-topbar">
      <div className="breadcrumbs"><span>{user.organizationName}</span><i>/</i><strong>{routes[route]}</strong></div>
      <div className="topbar-actions">
        {isCommand && <span className="topbar-status" style={{ background: st.bg, borderColor: st.border, color: st.color }}><span style={{ background: st.dot }} />{st.label}</span>}
        <button className="icon-button" aria-label="Уведомления"><Icon name="bell" size={18} /><b className={isCommand ? "" : "is-dot"}>{isCommand ? "2" : ""}</b></button>
        <span className="topbar-divider" />
        <button className="user-button" type="button"><span className="topbar-avatar">{initials(user.fullName, user.email)}</span><Icon name="chevron" size={14} /></button>
      </div>
    </header>
  );
}

function Shell({ route, setRoute, user, data, reload, onLogout }: { route: RouteKey; setRoute: (route: RouteKey) => void; user: SessionUser; data: AppData; reload: () => void; onLogout: () => void }) {
  return (
    <div className="hub-shell">
      <Sidebar route={route} user={user} setRoute={setRoute} />
      <div className="hub-main">
        <TopBar route={route} user={user} onLogout={onLogout} />
        <main className="hub-scroll">
          <div className="hub-page">
            {route === "command" && <CommandCenter data={data} setRoute={setRoute} />}
            {route === "departments" && <DepartmentsPage data={data} setRoute={setRoute} />}
            {route === "employees" && <EmployeesPage employees={data.employees} reload={reload} />}
            {route === "products" && <ProductsPage products={data.products} reload={reload} />}
            {route === "profile" && <ProfilePage user={user} onLogout={onLogout} />}
          </div>
        </main>
      </div>
    </div>
  );
}

function PageHeader({ title, text, action }: { title: string; text?: ReactNode; action?: ReactNode }) {
  return (
    <div className="page-header">
      <div><h1>{title}</h1>{text && <p>{text}</p>}</div>
      {action}
    </div>
  );
}

function StatusPill({ status }: { status: "normal" | "active" | "blocked" | "disabled" | "invited" }) {
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

function CommandCenter({ data, setRoute }: { data: AppData; setRoute: (route: RouteKey) => void }) {
  const [period, setPeriod] = useState<"today" | "d7" | "d30">("today");
  const vm = commandCenterModel(period);
  return (
    <>
      <div className="command-page-header">
        <div>
          <h1>Командный центр</h1>
          <p>Состояние компании одним взглядом · обновлено только что</p>
        </div>
        <div className="command-header-actions">
          <Segmented value={period} setValue={setPeriod} items={[["today", "Сегодня"], ["d7", "7 дней"], ["d30", "30 дней"]]} />
          <button className="refresh-button"><Icon name="refresh" size={15} />Обновить</button>
        </div>
      </div>

      <section className="company-status-banner" style={{ borderLeftColor: vm.st.dot }}>
        <div className="company-status-dot" style={{ background: vm.st.bg }}><span style={{ background: vm.st.dot }} /></div>
        <div className="company-status-text">
          <strong>Компания: {vm.st.label}</strong>
          <p>{vm.compSummary}</p>
        </div>
        <div className="company-status-metrics">
          <SmallMetric label="Отделы" value="1" />
          <SmallMetric label="Открытые диалоги" value={vm.m.open} />
          <SmallMetric label={`Выручка · ${vm.periodLabel}`} value={vm.m.rev} success />
        </div>
      </section>

      <div className="command-two-column">
        <section className="command-left">
          <div className="section-head">
            <h2>Отделы</h2>
            <span>1 активный</span>
          </div>
          <article className="sales-card">
            <div className="sales-head">
              <div className="sales-icon"><Icon name="shop" size={23} /></div>
              <div className="sales-title">
                <div>
                  <h3>Продажи</h3>
                  <StatusLabel vm={vm} />
                </div>
                <p>Ответственный: Анна Котова · 4 сотрудника · 1 AI-агент</p>
              </div>
              <button className="primary-button sales-open" onClick={() => setRoute("departments")}>Открыть отдел<Icon name="arrow" size={16} /></button>
            </div>
            <div className="dept-summary">{vm.deptSummary}</div>
            <MetricGroup title="ДИАЛОГИ — СЕЙЧАС" columns={5} items={[
              { label: "Открытые диалоги", value: vm.m.open },
              { label: "Активны за 15 мин", value: vm.m.active },
              { label: "На AI", value: vm.m.ai, dot: "#722ed1" },
              { label: "На операторах", value: vm.m.op, dot: "#1677ff" },
              { label: "Ожидают оператора", value: vm.m.wait, color: vm.m.waitColor },
            ]} />
            <MetricGroup title={`КОММЕРЦИЯ — ${vm.periodLabelUpper}`} columns={4} items={[
              { label: "Незавершённые платежи", value: vm.m.pend, color: vm.m.pendColor },
              { label: "Ошибки fulfillment", value: vm.m.ferr, color: vm.m.ferrColor },
              { label: "Продажи", value: vm.m.sales },
              { label: "Чистая выручка", value: vm.m.rev, color: "#389e0d" },
            ]} />
          </article>
        </section>

        <aside className="command-rail">
          <RailCard title="Требует внимания" icon="warning" iconColor="#faad14" count={String(vm.attention.length)} action="Все">
            {vm.attention.map((item) => (
              <a className="attention-row" href="#" onClick={(event) => event.preventDefault()} key={item.title}>
                <span style={{ background: item.dot }} />
                <span><strong>{item.title}</strong><small>{item.meta}</small></span>
                <em>{item.time}</em>
              </a>
            ))}
          </RailCard>
          <RailCard title="Состояние интеграций" icon="plug" iconColor="#595959" side={<span style={{ color: vm.intHeadColor }}>{vm.okCount}/6 в норме</span>}>
            {vm.integrations.map((item) => (
              <div className="integration-row" key={item.name}>
                <span style={{ background: item.dot }} />
                <span><strong>{item.name}</strong><small>{item.group}</small></span>
                <em style={{ color: item.statusColor }}>{item.statusLabel}</em>
              </div>
            ))}
          </RailCard>
          <section className="ai-spend-card">
            <div className="rail-card-head">
              <div><Icon name="bolt" size={17} /><strong>Расходы AI</strong></div>
              <span>{vm.periodLabel}</span>
            </div>
            <div className="ai-spend-main"><strong>{vm.aiSpendStr}</strong><span>из {vm.budgetStr}</span></div>
            <div className="ai-progress"><span style={{ width: `${vm.aiPct}%`, background: vm.aiBarColor }} /></div>
            <p>{vm.aiPct}% дневного бюджета</p>
            <div className="ai-grid">
              <SmallAiMetric label="Токены" value={vm.aiTokens} />
              <SmallAiMetric label="Диалоги" value={vm.aiDialogs} />
              <SmallAiMetric label="Цена диалога" value={vm.costPerDialog} />
            </div>
          </section>
        </aside>
      </div>
      <div className="command-updated">Обновлено: сегодня, 14:32 · детерминированная сводка</div>
    </>
  );
}

type CommandVm = ReturnType<typeof commandCenterModel>;

function commandCenterModel(period: "today" | "d7" | "d30") {
  const fmt = (n: number) => `₽${Math.round(n).toLocaleString("ru-RU").replace(/\u00a0/g, " ")}`;
  const ops = { open: 42, active: 9, ai: 35, op: 7, wait: 0, pend: 1, ferr: 0 };
  const com = {
    today: { label: "Сегодня", sales: 18, rev: 146200, aiSpend: 1240, budget: 5000, tokens: "412K", dlg: 42 },
    d7: { label: "7 дней", sales: 126, rev: 1024600, aiSpend: 8600, budget: 35000, tokens: "2,9M", dlg: 318 },
    d30: { label: "30 дней", sales: 540, rev: 4386000, aiSpend: 36400, budget: 150000, tokens: "12,4M", dlg: 1342 },
  }[period];
  const st = { label: "Нормально", color: "#389e0d", bg: "#f6ffed", border: "#b7eb8f", dot: "#52c41a" };
  const m = {
    open: String(ops.open),
    active: String(ops.active),
    ai: String(ops.ai),
    op: String(ops.op),
    wait: String(ops.wait),
    pend: String(ops.pend),
    ferr: String(ops.ferr),
    sales: String(com.sales),
    rev: fmt(com.rev),
    waitColor: "#262626",
    pendColor: "#262626",
    ferrColor: "#262626",
  };
  const attention = [
    { dot: "#faad14", title: "Незавершённый платёж · заказ ORD-10482", meta: "Продажи · Точка", time: "6 мин" },
    { dot: "#1677ff", title: "Подписка истекает через 2 дня · Foxray Pro", meta: "Продажи", time: "1 ч" },
  ];
  const integrations = [
    { name: "OpenRouter", group: "AI-провайдер", dot: "#52c41a", statusLabel: "Подключено", statusColor: "#52c41a" },
    { name: "Точка", group: "Платежи и фискализация", dot: "#52c41a", statusLabel: "Подключено", statusColor: "#52c41a" },
    { name: "MAX", group: "Канал", dot: "#52c41a", statusLabel: "Подключено", statusColor: "#52c41a" },
    { name: "Telegram", group: "Канал", dot: "#52c41a", statusLabel: "Подключено", statusColor: "#52c41a" },
    { name: "Web Chat", group: "Канал", dot: "#52c41a", statusLabel: "Подключено", statusColor: "#52c41a" },
    { name: "Fulfillment · FirePage", group: "Исполнение", dot: "#52c41a", statusLabel: "Подключено", statusColor: "#52c41a" },
  ];
  const aiPct = Math.round((com.aiSpend / com.budget) * 100);
  const aiBarColor = aiPct >= 85 ? "#ff4d4f" : aiPct >= 70 ? "#faad14" : "#1677ff";
  return {
    st,
    m,
    compSummary: "Все системы в норме. Один отдел активен, критичных событий нет.",
    deptSummary: "AI ведёт большинство диалогов. Очередь оператора пуста, незавершённых задач почти нет.",
    attention,
    integrations,
    okCount: "6",
    intHeadColor: "#389e0d",
    periodLabel: com.label,
    periodLabelUpper: com.label.toUpperCase(),
    aiSpendStr: fmt(com.aiSpend),
    budgetStr: fmt(com.budget),
    aiPct,
    aiBarColor,
    aiTokens: com.tokens,
    aiDialogs: String(com.dlg),
    costPerDialog: fmt(com.aiSpend / com.dlg),
  };
}

function StatusLabel({ vm }: { vm: CommandVm }) {
  return (
    <span className="command-status-label" style={{ background: vm.st.bg, borderColor: vm.st.border }}>
      <span style={{ background: vm.st.dot }} />
      <em style={{ color: vm.st.color }}>{vm.st.label}</em>
    </span>
  );
}

function SmallMetric({ label, value, success = false }: { label: string; value: string; success?: boolean }) {
  return <div><span>{label}</span><strong className={success ? "success" : ""}>{value}</strong></div>;
}

function MetricGroup({ title, columns, items }: { title: string; columns: 4 | 5; items: Array<{ label: string; value: string; color?: string; dot?: string }> }) {
  return (
    <>
      <div className="metric-group-title">{title}</div>
      <div className="metric-group-grid" style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}>
        {items.map((item) => (
          <div className="metric-cell" key={item.label}>
            <div>{item.dot && <span style={{ background: item.dot }} />}{item.label}</div>
            <strong style={{ color: item.color ?? "#262626" }}>{item.value}</strong>
          </div>
        ))}
      </div>
    </>
  );
}

function RailCard({ title, icon, iconColor, count, action, side, children }: { title: string; icon: "warning" | "plug"; iconColor: string; count?: string; action?: string; side?: ReactNode; children: ReactNode }) {
  return (
    <section className="rail-card">
      <div className="rail-card-head">
        <div><span className="rail-icon" style={{ color: iconColor }}><Icon name={icon} size={17} /></span><strong>{title}</strong>{count && <b>{count}</b>}</div>
        {action && <a href="#" onClick={(event) => event.preventDefault()}>{action}</a>}
        {side}
      </div>
      <div className="rail-card-body">{children}</div>
    </section>
  );
}

function SmallAiMetric({ label, value }: { label: string; value: string }) {
  return <div><span>{label}</span><strong>{value}</strong></div>;
}

function MetricCard({ label, value, sub, compact = false }: { label: string; value: number | string; sub: string; compact?: boolean }) {
  return <article className={`metric-card ${compact ? "is-compact" : ""}`}><span>{label}</span><strong>{value}</strong><small>{sub}</small></article>;
}

function DepartmentsPage({ data, setRoute }: { data: AppData; setRoute: (route: RouteKey) => void }) {
  const sales = data.departments.find((department) => department.code === "sales") ?? data.departments[0];
  return (
    <>
      <PageHeader title="Отделы" text={`Существующие отделы компании · ${data.departments.length} активный`} />
      {sales && (
        <div className="departments-grid">
          <section className="department-card">
            <div className="department-card-header">
              <div className="dept-icon"><Icon name="shop" size={24} /></div>
              <div className="department-card-title">
                <div>
                  <h2>{sales.name}</h2>
                  <StatusLabel vm={commandCenterModel("today")} />
                </div>
                <p>AI ведёт большинство диалогов, очередь оператора пуста.</p>
              </div>
            </div>

            <div className="department-meta">
              <div>
                <span>Ответственный</span>
                <strong className="owner-person"><i>АК</i>Анна Котова</strong>
              </div>
              <div>
                <span>Состав</span>
                <strong>4 сотрудника · 1 AI-агент</strong>
              </div>
              <div>
                <span>Связанные продукты</span>
                <strong className="product-tags">{data.products.map((product) => <ProductTag product={product} key={product.id} />)}</strong>
              </div>
            </div>

            <div className="department-stats">
              <div><span>Открытые диалоги</span><strong>42</strong></div>
              <div><span>Продажи · сегодня</span><strong>18</strong></div>
              <div><span>Выручка</span><strong className="success">₽146 200</strong></div>
            </div>

            <div className="department-action">
              <a href="#" onClick={(event) => event.preventDefault()}>Открыть отдел<Icon name="arrow" size={16} /></a>
            </div>
          </section>
        </div>
      )}
      <p className="muted-note">Новые отделы появятся здесь по мере их создания.</p>
    </>
  );
}

function EmployeesPage({ employees, reload }: { employees: Employee[]; reload: () => void }) {
  const [role, setRole] = useState<"all" | Role>("all");
  const [status, setStatus] = useState<"all" | "active" | "invited" | "blocked">("all");
  const [query, setQuery] = useState("");
  const [menuId, setMenuId] = useState<number | null>(null);
  const filtered = employees.filter((employee) => {
    const employeeStatus = employeeStatusKey(employee);
    const q = query.trim().toLowerCase();
    return (
      (role === "all" || employee.role === role) &&
      (status === "all" || employeeStatus === status) &&
      (!q || employee.fullName.toLowerCase().includes(q) || employee.email.toLowerCase().includes(q))
    );
  });
  async function block(employee: Employee) {
    if (employee.role === "OWNER" || employee.isBlocked) return;
    await api(`/api/v1/employees/${employee.id}/block/`, { method: "POST" });
    setMenuId(null);
    reload();
  }
  const resetFilters = () => {
    setQuery("");
    setRole("all");
    setStatus("all");
    setMenuId(null);
  };
  return (
    <>
      {menuId !== null && <button className="menu-scrim" aria-label="Закрыть меню" onClick={() => setMenuId(null)} />}
      <PageHeader
        title="Сотрудники"
        text={<>Доступ к Hub · показано <b>{filtered.length}</b> из {employees.length}</>}
        action={<button className="primary-button" type="button"><Icon name="team" size={16} />Добавить оператора</button>}
      />
      <div className="filter-bar employees-filter">
        <label className="employee-search">
          <Icon name="search" size={15} />
          <input value={query} onChange={(event) => { setQuery(event.target.value); setMenuId(null); }} placeholder="Поиск по имени или email…" />
        </label>
        <div className="filter-group">
          <span>Роль</span>
          <Segmented value={role} setValue={(nextRole) => { setRole(nextRole); setMenuId(null); }} items={[["all", "Все"], ["OWNER", "OWNER"], ["OPERATOR", "OPERATOR"]]} />
        </div>
        <div className="filter-group">
          <span>Статус</span>
          <Segmented value={status} setValue={(nextStatus) => { setStatus(nextStatus); setMenuId(null); }} items={[["all", "Все"], ["active", "Активные"], ["invited", "Приглашённые"], ["blocked", "Заблокированные"]]} />
        </div>
        <button className="reset-filter" type="button" onClick={resetFilters}>Сбросить</button>
      </div>
      <div className="table-card employees-card">
        <div className="table-scroll">
          <table className="baseline-table employees-table">
            <thead><tr><th>СОТРУДНИК</th><th>РОЛЬ</th><th>ОТДЕЛ</th><th>СТАТУС</th><th>ПОСЛЕДНИЙ ВХОД</th><th className="numeric">ДИАЛОГИ</th><th /></tr></thead>
            <tbody>
              {filtered.map((employee) => <EmployeeRow employee={employee} block={block} menuId={menuId} setMenuId={setMenuId} key={employee.id} />)}
            </tbody>
          </table>
        </div>
        {!filtered.length && <EmptyState title="Сотрудники не найдены" />}
        <div className="employees-footer">
          <span>Показано {filtered.length} из {employees.length}</span>
          <span>Сессии и пароли управляются в карточке сотрудника</span>
        </div>
      </div>
    </>
  );
}

function employeeStatusKey(employee: Employee): "active" | "invited" | "blocked" {
  if (employee.isBlocked) return "blocked";
  if (employee.mustChangePassword) return "invited";
  return "active";
}

function EmployeeRow({ employee, block, menuId, setMenuId }: { employee: Employee; block: (employee: Employee) => void; menuId: number | null; setMenuId: (id: number | null) => void }) {
  const dialogs = "0";
  const status = employeeStatusKey(employee);
  const menuOpen = menuId === employee.id;
  return (
    <tr>
      <td><div className="person-cell"><Avatar employee={employee} /><span><strong>{employee.fullName || employee.email}</strong><small>{employee.email}</small></span></div></td>
      <td><RoleBadge role={employee.role} /></td>
      <td>{employee.department === "sales" ? "Продажи" : "—"}</td>
      <td><StatusPill status={status} /></td>
      <td>{employee.role === "OWNER" ? "сейчас · онлайн" : "не входил"}</td>
      <td className={`numeric ${dialogs === "0" ? "muted-number" : ""}`}>{dialogs}</td>
      <td className="row-actions">
        <button className="row-menu-button" aria-label="Действия сотрудника" onClick={() => setMenuId(menuOpen ? null : employee.id)}><Icon name="more" /></button>
        {menuOpen && (
          <div className="row-menu">
            <a href="#" onClick={(event) => event.preventDefault()}><Icon name="external" size={15} />Открыть карточку</a>
            <a href="#" onClick={(event) => event.preventDefault()}><Icon name="logout" size={15} />Завершить сессии</a>
            <a href="#" onClick={(event) => event.preventDefault()}><Icon name="key" size={15} />Сбросить пароль</a>
            <span />
            <button className={employee.isBlocked ? "success" : "danger"} onClick={() => block(employee)} disabled={employee.role === "OWNER" || employee.isBlocked}>{employee.isBlocked ? "Разблокировать" : "Заблокировать"}</button>
          </div>
        )}
      </td>
    </tr>
  );
}

function RoleBadge({ role }: { role: Role }) {
  return <span className={`role-badge ${role.toLowerCase()}`}>{role}</span>;
}

type ProductPeriod = "today" | "d7" | "d30";

function ProductsPage({ products, reload }: { products: Product[]; reload: () => void }) {
  const [period, setPeriod] = useState<ProductPeriod>("d30");
  const [menuId, setMenuId] = useState<number | null>(null);
  const periodLabel = { today: "Сегодня", d7: "7 дней", d30: "30 дней" }[period];
  async function deactivate(product: Product) {
    if (product.status === "DISABLED") return;
    await api(`/api/v1/company/products/${product.id}/deactivate/`, { method: "POST" });
    setMenuId(null);
    reload();
  }
  return (
    <>
      {menuId !== null && <button className="menu-scrim" aria-label="Закрыть меню" onClick={() => setMenuId(null)} />}
      <PageHeader
        title="Продукты"
        text={`${products.filter((item) => item.status === "ACTIVE").length} активных продукта · цены и Offer управляются в карточке продукта`}
        action={(
          <div className="products-header-actions">
            <Segmented value={period} setValue={(nextPeriod) => { setPeriod(nextPeriod); setMenuId(null); }} items={[["today", "Сегодня"], ["d7", "7 дней"], ["d30", "30 дней"]]} />
            <button className="primary-button" type="button"><Icon name="plus" size={16} />Создать продукт</button>
          </div>
        )}
      />
      <div className="table-card products-card">
        <div className="product-table-scroll">
          <table className="baseline-table products-table">
            <thead><tr><th>ПРОДУКТ</th><th>СТАТУС</th><th>OFFER И ЦЕНЫ</th><th>SALES-AGENT</th><th>КАНАЛЫ</th><th>FULFILLMENT</th><th className="numeric">ПРОДАЖИ · {periodLabel.toUpperCase()}</th><th /></tr></thead>
            <tbody>{products.map((product) => <ProductRow product={product} period={period} menuId={menuId} setMenuId={setMenuId} deactivate={deactivate} key={product.id} />)}</tbody>
          </table>
        </div>
        <div className="products-footer">
          <span>{products.length} продукта</span>
          <span>Активная цена не редактируется задним числом — создаётся новая версия</span>
        </div>
      </div>
    </>
  );
}

function ProductRow({ product, period, menuId, setMenuId, deactivate }: { product: Product; period: ProductPeriod; menuId: number | null; setMenuId: (id: number | null) => void; deactivate: (product: Product) => void }) {
  const accent = productAccent(product.code);
  const details = productDetails(product);
  const sales = details.sales[period];
  const menuOpen = menuId === product.id;
  return (
    <tr>
      <td><div className="product-cell"><span className="product-icon" style={{ background: accent.bg, color: accent.color }}><Icon name="box" size={21} /></span><span><strong>{product.name}</strong><small>{details.sub}</small></span></div></td>
      <td><StatusPill status={product.status === "ACTIVE" ? "active" : "disabled"} /></td>
      <td>
        <div className="offer-list">
          {details.offers.map((offer) => <div key={`${product.id}-${offer.name}`}><span>{offer.name} <em>· {offer.type}</em></span><strong>{offer.price}</strong></div>)}
          {details.note && <p><Icon name="percent" size={11} />{details.note}</p>}
        </div>
      </td>
      <td><div className="agent-state"><span><i />AI-агент</span><small>{details.agentRelease}</small></div></td>
      <td><div className="channel-tags">{details.channels.map((channel) => <span style={{ background: channel.bg, color: channel.color }} key={channel.label}><i style={{ background: channel.color }} />{channel.label}</span>)}</div></td>
      <td><div className="fulfillment-state"><span><i />Подключён</span><small>{details.fulfillment}</small></div></td>
      <td className="numeric"><div className="product-sales"><strong>{sales.sum}</strong><small>{sales.n} продаж</small></div></td>
      <td className="row-actions">
        <button className="row-menu-button" aria-label="Действия продукта" onClick={() => setMenuId(menuOpen ? null : product.id)}><Icon name="more" /></button>
        {menuOpen && (
          <div className="row-menu product-row-menu">
            <a href="#" onClick={(event) => event.preventDefault()}><Icon name="external" size={15} />Открыть продукт</a>
            <a href="#" onClick={(event) => event.preventDefault()}><Icon name="plus" size={15} />Добавить Offer</a>
            <span />
            <button className="warning" onClick={() => deactivate(product)} disabled={product.status === "DISABLED"}><Icon name="pause" size={15} />Деактивировать</button>
          </div>
        )}
      </td>
    </tr>
  );
}

function productDetails(product: Product) {
  const base = {
    sub: product.siteUrl || product.code,
    offers: [{ name: "—", type: "—", price: "—" }],
    note: "",
    agentRelease: "release —",
    channels: [] as Array<{ label: string; color: string; bg: string }>,
    fulfillment: "—",
    sales: {
      today: { n: 0, sum: "₽0" },
      d7: { n: 0, sum: "₽0" },
      d30: { n: 0, sum: "₽0" },
    },
  };
  const channels = {
    max: { label: "MAX", color: "#6b5be0", bg: "#f2f0ff" },
    tg: { label: "TG", color: "#2f8fd0", bg: "#eaf6fd" },
    web: { label: "Web", color: "#0f9b8e", bg: "#e8f7f4" },
  };
  if (product.code === "firepage") {
    return {
      sub: "Нишевые сайты · коробка",
      offers: [
        { name: "Коробка", type: "разовая", price: "₽4 900" },
        { name: "Годовая поддержка", type: "продление", price: "₽1 470 / год" },
      ],
      note: "Поддержка — 30% от цены коробки",
      agentRelease: "release v4 · published",
      channels: [channels.max, channels.tg, channels.web],
      fulfillment: "Сборка и выдача сайта",
      sales: {
        today: { n: 2, sum: "₽9 800" },
        d7: { n: 14, sum: "₽71 540" },
        d30: { n: 56, sum: "₽288 100" },
      },
    };
  }
  if (product.code === "foxray") {
    return {
      sub: "SaaS · подписка",
      offers: [
        { name: "Pro", type: "подписка", price: "₽4 900 / мес" },
        { name: "Max", type: "подписка", price: "₽9 900 / мес" },
      ],
      note: "Скидка 20% при оплате за год",
      agentRelease: "release v3 · published",
      channels: [channels.max, channels.tg, channels.web],
      fulfillment: "Выдача доступа",
      sales: {
        today: { n: 3, sum: "₽16 400" },
        d7: { n: 19, sum: "₽104 200" },
        d30: { n: 82, sum: "₽548 700" },
      },
    };
  }
  return base;
}

function ProductTag({ product }: { product: Product }) {
  const accent = productAccent(product.code);
  return <span style={{ background: accent.bg, color: accent.color }}>{product.name}</span>;
}

function ProfilePage({ user, onLogout }: { user: SessionUser; onLogout: () => void }) {
  return (
    <div className="profile-stack">
      <section className="profile-header-card">
        <Avatar user={user} />
        <div className="profile-header-main">
          <div><h1>{user.fullName || user.email}</h1><RoleBadge role={user.role} /></div>
          <p>{user.email}</p>
        </div>
        <button className="danger-outline" onClick={onLogout}><Icon name="logout" size={15} />Выйти</button>
      </section>
      <section className="profile-card">
        <h3>Личные данные</h3>
        <div className="profile-grid">
          <ReadOnlyField label="Имя" value={user.fullName || user.email} editable />
          <ReadOnlyField label="Email · используется для входа" value={user.email} editable mono />
          <ReadOnlyField label="Роль" value={user.role} />
        </div>
        <div className="profile-actions"><button className="primary-button">Сохранить</button></div>
      </section>
      <section className="profile-card">
        <h3>Смена пароля</h3>
        <div className="password-fields">
          <PasswordField label="Текущий пароль" value="········" />
          <PasswordField label="Новый пароль" placeholder="мин. 10 символов" />
          <PasswordField label="Повторите новый пароль" />
        </div>
        <div className="profile-actions"><button className="secondary-button">Обновить пароль</button></div>
      </section>
      <section className="profile-card totp-card">
        <div>
          <h3>Двухфакторная аутентификация (TOTP)</h3>
          <p>{user.totpEnabled ? "Включена. Для OWNER рекомендуется держать включённой." : "Отключена. Для роли OWNER настоятельно рекомендуется включить."}</p>
        </div>
        <span className={`totp-switch ${user.totpEnabled ? "on" : ""}`}><i /></span>
        {user.totpEnabled && <div className="security-note ok">Приложение-аутентификатор подключено · последний код принят 5 мин назад</div>}
      </section>
      <section className="sessions-card">
        <div className="sessions-head"><h3>Активные сессии</h3><button>Завершить другие сессии</button></div>
        <div className="session-row"><span className="session-icon"><Icon name="user" /></span><span><strong>Браузер</strong><small>сейчас активна</small></span><b>текущая</b></div>
      </section>
    </div>
  );
}

function ReadOnlyField({ label, value, editable = false, mono = false }: { label: string; value: string; editable?: boolean; mono?: boolean }) {
  return <label className="readonly-field"><span>{label}</span><input className={mono ? "mono" : ""} value={value} disabled={!editable} readOnly /></label>;
}

function PasswordField({ label, value = "", placeholder = "" }: { label: string; value?: string; placeholder?: string }) {
  return <label className="readonly-field"><span>{label}</span><input type="password" value={value} placeholder={placeholder} readOnly /></label>;
}

function Segmented<T extends string>({ value, setValue, items }: { value: T; setValue: (value: T) => void; items: Array<[T, string]> }) {
  return <div className="segmented">{items.map(([key, label]) => <button className={value === key ? "active" : ""} onClick={() => setValue(key)} key={key}>{label}</button>)}</div>;
}

function EmptyState({ title }: { title: string }) {
  return <div className="empty-state"><strong>{title}</strong></div>;
}

function LoadingScreen() {
  return <main className="state-screen"><div className="state-card">Загрузка</div></main>;
}

function ErrorScreen({ retry }: { retry: () => void }) {
  return <main className="state-screen"><div className="state-card"><strong>Ошибка загрузки</strong><button className="primary-button" onClick={retry}>Повторить</button></div></main>;
}

export function App() {
  const [sessionLoading, setSessionLoading] = useState(true);
  const [user, setUser] = useState<SessionUser | null>(null);
  const [totpChallenge, setTotpChallenge] = useState<AuthChallenge | null>(null);
  const [route, setRoute] = useState<RouteKey>("command");
  const [data, setData] = useState<AppData>({ employees: [], departments: [], products: [] });
  const [dataError, setDataError] = useState(false);

  const loadData = useMemo(() => async () => {
    setDataError(false);
    try {
      const [employees, departments, products] = await Promise.all([
        api<{ items: Employee[] }>("/api/v1/employees/"),
        api<{ items: Department[] }>("/api/v1/company/departments/"),
        api<{ items: Product[] }>("/api/v1/company/products/"),
      ]);
      setData({ employees: employees.items, departments: departments.items, products: products.items });
    } catch {
      setDataError(true);
    }
  }, []);

  useEffect(() => {
    api<{ authenticated: boolean; user?: SessionUser }>("/api/v1/auth/session/")
      .then((payload) => {
        if (payload.authenticated && payload.user) {
          setUser(payload.user);
        }
      })
      .finally(() => setSessionLoading(false));
  }, []);

  useEffect(() => {
    if (user) void loadData();
  }, [loadData, user]);

  async function logout() {
    await api("/api/v1/auth/logout/", { method: "POST" }).catch(() => undefined);
    setUser(null);
    setTotpChallenge(null);
    setRoute("command");
    setData({ employees: [], departments: [], products: [] });
  }

  if (sessionLoading) return <ConfigProvider theme={edevsHubTheme}><LoadingScreen /></ConfigProvider>;

  return (
    <ConfigProvider theme={edevsHubTheme}>
      {totpChallenge ? (
        <AuthTotpCode challenge={totpChallenge} onVerified={(nextUser) => { setTotpChallenge(null); setUser(nextUser); }} />
      ) : !user ? (
        <AuthLogin onLogin={(nextUser) => { setUser(nextUser); void loadData(); }} onTotpChallenge={setTotpChallenge} />
      ) : user.mustChangePassword ? (
        <AuthChangePassword user={user} onChanged={setUser} />
      ) : user.totpRequired && !user.totpEnabled ? (
        <AuthTotpSetup user={user} onConfirmed={setUser} />
      ) : dataError ? (
        <ErrorScreen retry={loadData} />
      ) : (
        <Shell route={route} setRoute={setRoute} user={user} data={data} reload={loadData} onLogout={logout} />
      )}
    </ConfigProvider>
  );
}

import { type FormEvent, type ReactNode, useEffect, useState } from "react";

import { api } from "../../api/client";
import type { AuthChallenge, LoginPayload, SessionUser } from "../../types";
import { Icon, PulseIcon, ShieldIcon } from "../../shared/icons";
import { initials } from "../../shared/utils";

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

export function AuthLogin({ onLogin, onTotpChallenge }: { onLogin: (user: SessionUser) => void; onTotpChallenge: (challenge: AuthChallenge) => void }) {
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

export function AuthChangePassword({ onChanged }: { user: SessionUser; onChanged: (user: SessionUser) => void }) {
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

export function AuthTotpSetup({ user, onConfirmed }: { user: SessionUser; onConfirmed: (user: SessionUser) => void }) {
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

export function AuthTotpCode({ challenge, onVerified }: { challenge: AuthChallenge; onVerified: (user: SessionUser) => void }) {
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

import { type FormEvent, type ReactNode, useEffect, useState } from "react";

import { api } from "../../api/client";
import type { AuthChallenge, LoginPayload, SessionUser } from "../../types";
import { Icon, PulseIcon, ShieldIcon } from "../../shared/icons";
import { createQrMatrix } from "./qr";

function AuthFrame({ title, subtitle, logo, width = 400, children, note }: { title: string; subtitle: ReactNode; logo: "pulse" | "shield"; width?: number; children: ReactNode; note?: ReactNode }) {
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

function AuthCodeInput({ value, onChange, error = false, autoFocus = false }: { value: string; onChange: (value: string) => void; error?: boolean; autoFocus?: boolean }) {
  const activeIndex = Math.min(value.length, 5);
  const digits = value.padEnd(6, " ").slice(0, 6).split("");
  return (
    <div className="auth-code-input-wrap">
      <div className="auth-code-cells">
        {digits.map((digit, index) => {
          const filled = digit.trim().length > 0;
          const active = !error && index === activeIndex && value.length < 6;
          return <span className={`${filled ? "filled" : ""} ${active ? "active" : ""} ${error ? "error" : ""}`} key={index}>{digit}</span>;
        })}
      </div>
      <input
        className="auth-code-input-hidden"
        value={value}
        onChange={(event) => onChange(event.target.value.replace(/\D/g, "").slice(0, 6))}
        inputMode="numeric"
        maxLength={6}
        autoFocus={autoFocus}
        aria-label="Код из приложения-аутентификатора"
      />
    </div>
  );
}

function TotpQr({ value }: { value: string }) {
  const qr = createQrMatrix(value);
  return (
    <div className="auth-qr-shell">
      <div className="auth-qr-grid" style={{ gridTemplateColumns: `repeat(${qr.size}, 1fr)` }} aria-label="QR-код для подключения TOTP">
        {qr.modules.map((active, index) => <span className={active ? "active" : ""} key={index} />)}
      </div>
    </div>
  );
}

function formatCountdown(seconds: number): string {
  return `0:${seconds.toString().padStart(2, "0")}`;
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

export function AuthTotpSetup({ user: _user, onConfirmed }: { user: SessionUser; onConfirmed: (user: SessionUser) => void }) {
  const [secret, setSecret] = useState("");
  const [otpauthUrl, setOtpauthUrl] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api<{ secret: string; otpauthUrl: string }>("/api/v1/auth/totp/setup/")
      .then((payload) => {
        setSecret(payload.secret);
        setOtpauthUrl(payload.otpauthUrl);
      })
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

  async function copySecret() {
    if (!secret) return;
    try {
      await navigator.clipboard.writeText(secret);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  }

  return (
    <AuthFrame title="Подключение двухфакторной аутентификации" subtitle="Отсканируйте QR-код в приложении-аутентификаторе, затем подтвердите кодом" logo="shield" width={440}>
      <form className="auth-card auth-totp-setup-card" onSubmit={submit}>
        <div className="auth-totp-step">
          <span>1</span>
          <strong>Отсканируйте QR-код</strong>
        </div>
        <TotpQr value={otpauthUrl || secret} />
        <p className="auth-secret-caption">Не получается отсканировать? Введите ключ вручную:</p>
        <div className="auth-secret-row">
          <code>{secret || "Загрузка ключа"}</code>
          <button type="button" onClick={copySecret} title="Скопировать" disabled={!secret}>
            <Icon name={copied ? "check" : "copy"} size={15} />
          </button>
        </div>
        <div className="auth-totp-divider" />
        <div className="auth-totp-step second">
          <span>2</span>
          <strong>Введите код из приложения</strong>
        </div>
        <AuthCodeInput value={code} onChange={(nextCode) => { setCode(nextCode); setError(false); }} error={error} autoFocus />
        {error && <div className="auth-inline-error setup-error"><Icon name="warning" size={14} />Код не совпал. Попробуйте ещё раз</div>}
        <button className="primary-button auth-submit" type="submit" disabled={code.length !== 6 || submitting}>Активировать</button>
      </form>
      <div className="auth-cancel-link"><a href="#" onClick={(event) => event.preventDefault()}>Отмена</a></div>
    </AuthFrame>
  );
}

export function AuthTotpCode({ challenge, onVerified }: { challenge: AuthChallenge; onVerified: (user: SessionUser) => void }) {
  const [code, setCode] = useState("");
  const [error, setError] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [countdown, setCountdown] = useState(30 - (Math.floor(Date.now() / 1000) % 30));

  useEffect(() => {
    const timer = window.setInterval(() => setCountdown(30 - (Math.floor(Date.now() / 1000) % 30)), 1000);
    return () => window.clearInterval(timer);
  }, []);

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
    <AuthFrame title="Подтверждение входа" subtitle={<>Введите 6-значный код из приложения-аутентификатора для <b>{challenge.email}</b></>} logo="shield">
      <form className="auth-card auth-totp-code-card" onSubmit={submit}>
        <AuthCodeInput value={code} onChange={(nextCode) => { setCode(nextCode); setError(false); }} error={error} autoFocus />
        {error && <div className="auth-error totp-code-error"><Icon name="warning" size={15} /><span>Неверный код. Осталось попыток: 2</span></div>}
        <button className="primary-button auth-submit" type="submit" disabled={code.length !== 6 || submitting}>Подтвердить</button>
        <div className="auth-countdown"><Icon name="clock" size={14} />Код обновится через <span>{formatCountdown(countdown)}</span></div>
      </form>
      <p className="auth-support-link">Нет доступа к коду? <a href="#" onClick={(event) => event.preventDefault()}>Связаться с поддержкой</a></p>
    </AuthFrame>
  );
}

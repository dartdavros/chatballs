import { type FormEvent, useState } from "react";

import { api } from "../../api/client";
import type { AuthChallenge, AuthenticatedUser, LoginPayload } from "../../types";
import { Icon } from "../../shared/icons";
import { Button } from "../../shared/ui-controls";
import { AuthField } from "./AuthField";
import { AuthFrame } from "./AuthFrame";

export function AuthLogin({ onLogin, onTotpChallenge, onRecover }: { onLogin: (user: AuthenticatedUser) => void; onTotpChallenge: (challenge: AuthChallenge) => void; onRecover: () => void }) {
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
    <AuthFrame title="CustoCRM" subtitle="Рабочая область организации" logo="pulse" note="Защищённое соединение">
      <form className="auth-card" onSubmit={submit}>
        {error && <div className="auth-error"><span className="auth-error-dot">!</span><span>Неверный email или пароль. Проверьте данные и попробуйте снова.</span></div>}
        <label className="field-label">Email</label>
        <AuthField icon="mail" value={email} onChange={(nextEmail) => { setEmail(nextEmail); setError(false); }} placeholder="you@domain.ru" error={error} />
        <div className="password-row">
          <label className="field-label">Пароль</label>
          <a href="#" onClick={(event) => { event.preventDefault(); onRecover(); }}>Восстановить доступ</a>
        </div>
        <AuthField icon="lock" value={password} onChange={(nextPassword) => { setPassword(nextPassword); setError(false); }} placeholder="Пароль" type={show ? "text" : "password"} variant="auth-password" error={error}>
          <button type="button" onClick={() => setShow((value) => !value)} aria-label={show ? "Скрыть пароль" : "Показать пароль"}>
            <Icon name={show ? "eyeOff" : "eye"} size={17} />
          </button>
        </AuthField>
        <Button className="auth-submit" icon="arrow" iconSize={16} type="submit" variant="primary" disabled={submitting}>Войти</Button>
      </form>
    </AuthFrame>
  );
}

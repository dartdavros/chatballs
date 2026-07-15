import { type FormEvent, useEffect, useState } from "react";

import { api } from "../../api/client";
import type { AuthChallenge, AuthenticatedUser } from "../../types";
import { Icon } from "../../shared/icons";
import { Button } from "../../shared/ui-controls";
import { AuthCodeInput } from "./AuthCodeInput";
import { AuthFrame } from "./AuthFrame";
import { formatCountdown } from "./time";

export function AuthTotpCode({ challenge, onVerified }: { challenge: AuthChallenge; onVerified: (user: AuthenticatedUser) => void }) {
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
      const payload = await api<{ authenticated: true; user: AuthenticatedUser }>("/api/v1/auth/totp/verify/", {
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
        <Button className="auth-submit" type="submit" variant="primary" disabled={code.length !== 6 || submitting}>Подтвердить</Button>
        <div className="auth-countdown"><Icon name="clock" size={14} />Код обновится через <span>{formatCountdown(countdown)}</span></div>
      </form>
      <p className="auth-support-link">Нет доступа к коду? <a href="#" onClick={(event) => event.preventDefault()}>Связаться с поддержкой</a></p>
    </AuthFrame>
  );
}

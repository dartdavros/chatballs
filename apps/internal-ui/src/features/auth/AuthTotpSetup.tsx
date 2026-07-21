import { type FormEvent, useEffect, useState } from "react";

import { api } from "../../api/client";
import type { AuthenticatedUser, SessionUser } from "../../types";
import { Icon } from "../../shared/icons";
import { Button } from "../../shared/ui-controls";
import { AuthCodeInput } from "./AuthCodeInput";
import { AuthFrame } from "./AuthFrame";
import { TotpQr } from "./TotpQr";

export function AuthTotpSetup({ user: _user, onConfirmed }: { user: SessionUser; onConfirmed: (user: AuthenticatedUser) => void }) {
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
      const payload = await api<{ authenticated: true; user: AuthenticatedUser }>("/api/v1/auth/totp/confirm/", {
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
        <div className="auth-totp-step"><span>1</span><strong>Отсканируйте QR-код</strong></div>
        <TotpQr value={otpauthUrl || secret} />
        <p className="auth-secret-caption">Не получается отсканировать? Введите ключ вручную:</p>
        <div className="auth-secret-row">
          <code>{secret || "Загрузка ключа"}</code>
          <button type="button" onClick={copySecret} title="Скопировать" disabled={!secret}><Icon name={copied ? "check" : "copy"} size={15} /></button>
        </div>
        <div className="auth-totp-divider" />
        <div className="auth-totp-step second"><span>2</span><strong>Введите код из приложения</strong></div>
        <AuthCodeInput value={code} onChange={(nextCode) => { setCode(nextCode); setError(false); }} error={error} autoFocus />
        {error && <div className="auth-inline-error setup-error"><Icon name="warning" size={14} />Код не совпал. Попробуйте ещё раз</div>}
        <Button className="auth-submit" type="submit" variant="primary" disabled={code.length !== 6 || submitting}>Активировать</Button>
      </form>
      <div className="auth-cancel-link"><button className="link is-muted" type="button">Отмена</button></div>
    </AuthFrame>
  );
}

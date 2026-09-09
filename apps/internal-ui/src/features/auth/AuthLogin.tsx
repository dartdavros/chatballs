import { type FormEvent, useState } from "react";

import { api } from "../../api/client";
import type { AuthChallenge, AuthenticatedUser, LoginPayload } from "../../types";
import { Icon } from "../../shared/icons";
import { Button } from "../../shared/ui-controls";
import { AuthField } from "./AuthField";
import { AuthFrame } from "./AuthFrame";
import { t } from "../../i18n";

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
    <AuthFrame title="Chatballs" subtitle={t("admin.good_see")} logo="pulse" note={t("admin.secure_connection")}>
      <form className="auth-card" onSubmit={submit}>
        {error && <div className="auth-error"><span className="auth-error-dot">!</span><span>{t("admin.wrong_email_or_password_check")}</span></div>}
        <label className="field-label">Email</label>
        <AuthField icon="mail" value={email} onChange={(nextEmail) => { setEmail(nextEmail); setError(false); }} placeholder="you@domain.ru" error={error} />
        <div className="password-row">
          <label className="field-label">{t("common.password")}</label>
          <button className="link" type="button" onClick={onRecover}>{t("admin.recover_access")}</button>
        </div>
        <AuthField icon="lock" value={password} onChange={(nextPassword) => { setPassword(nextPassword); setError(false); }} placeholder={t("common.password")} type={show ? "text" : "password"} variant="auth-password" error={error}>
          <button type="button" onClick={() => setShow((value) => !value)} aria-label={show ? t("admin.hide_password") : t("admin.show_password")}>
            <Icon name={show ? "eyeOff" : "eye"} size={17} />
          </button>
        </AuthField>
        <Button className="auth-submit" icon="arrow" iconSize={16} type="submit" variant="primary" disabled={submitting}>{t("admin.sign")}</Button>
      </form>
    </AuthFrame>
  );
}

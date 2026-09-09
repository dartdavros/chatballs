import { type FormEvent, useEffect, useState } from "react";

import { api } from "../../api/client";
import type { AuthenticatedUser, SessionUser } from "../../types";
import { Icon, LogoSpinner } from "../../shared/icons";
import { Button } from "../../shared/ui-controls";
import { AuthCodeInput } from "./AuthCodeInput";
import { AuthFrame } from "./AuthFrame";
import { TotpQr } from "./TotpQr";
import { t } from "../../i18n";

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
    <AuthFrame title={t("admin.setting_up_two_factor_authentication")} subtitle={t("admin.scan_qr_code_authenticator_app")} logo="shield" width={440}>
      <form className="auth-card auth-totp-setup-card" onSubmit={submit}>
        <div className="auth-totp-step"><span>1</span><strong>{t("admin.scan_qr_code")}</strong></div>
        <TotpQr value={otpauthUrl || secret} />
        <p className="auth-secret-caption">{t("admin.cannot_scan_enter_key_manually")}</p>
        <div className="auth-secret-row">
          <code>{secret || <LogoSpinner size={16} />}</code>
          <button type="button" onClick={copySecret} title={t("common.copy_clipboard")} disabled={!secret}><Icon name={copied ? "check" : "copy"} size={15} /></button>
        </div>
        <div className="auth-totp-divider" />
        <div className="auth-totp-step second"><span>2</span><strong>{t("admin.enter_code_from_app")}</strong></div>
        <AuthCodeInput value={code} onChange={(nextCode) => { setCode(nextCode); setError(false); }} error={error} autoFocus />
        {error && <div className="auth-inline-error setup-error"><Icon name="warning" size={14} />{t("admin.code_did_not_match_try")}</div>}
        <Button className="auth-submit" type="submit" variant="primary" disabled={code.length !== 6 || submitting}>{t("admin.activate")}</Button>
      </form>
      <div className="auth-cancel-link"><button className="link is-muted" type="button">{t("common.cancel")}</button></div>
    </AuthFrame>
  );
}

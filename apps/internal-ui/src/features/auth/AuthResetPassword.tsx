import { type FormEvent, useEffect, useState } from "react";

import { api } from "../../api/client";
import { Icon } from "../../shared/icons";
import { Button } from "../../shared/ui-controls";
import { AuthField } from "./AuthField";
import { AuthFrame } from "./AuthFrame";
import { passwordIsValid, passwordLabels, passwordScore } from "./password";
import { t } from "../../i18n";

type Status = "checking" | "form" | "invalid" | "done";

export function AuthResetPassword({ onDone }: { onDone: () => void }) {
  const params = new URLSearchParams(window.location.search);
  const uid = params.get("uid") ?? "";
  const token = params.get("token") ?? "";

  const [status, setStatus] = useState<Status>("checking");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const score = passwordScore(password);
  const mismatch = confirm.length > 0 && password !== confirm;
  const valid = passwordIsValid(password, mismatch);

  useEffect(() => {
    let active = true;
    if (!uid || !token) {
      setStatus("invalid");
      return;
    }
    api<{ valid: boolean }>(`/api/v1/auth/password-reset/validate/?uid=${encodeURIComponent(uid)}&token=${encodeURIComponent(token)}`)
      .then((payload) => { if (active) setStatus(payload.valid ? "form" : "invalid"); })
      .catch(() => { if (active) setStatus("invalid"); });
    return () => { active = false; };
  }, [uid, token]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!valid || submitting) return;
    setSubmitting(true);
    setError("");
    try {
      await api("/api/v1/auth/password-reset/confirm/", { method: "POST", body: JSON.stringify({ uid, token, newPassword: password }) });
      setStatus("done");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : t("admin.could_not_save_password"));
    } finally {
      setSubmitting(false);
    }
  }

  const backLink = (
    <button type="button" className="auth-back-login" onClick={onDone}><Icon name="arrow" size={14} />{t("common.back_sign")}</button>
  );

  if (status === "checking") {
    return (
      <AuthFrame title={t("admin.checking_link")} subtitle={t("admin.one_moment")} logo="shield">
        <div className="auth-card"><p className="auth-hint">{t("admin.checking_password_reset_link")}</p></div>
      </AuthFrame>
    );
  }

  if (status === "invalid") {
    return (
      <AuthFrame title={t("admin.link_not_valid")} subtitle={t("admin.link_has_expired_or_has")} logo="shield" note={backLink}>
        <div className="auth-card">
          <div className="auth-recovery-sent">
            <div className="auth-recovery-sent-icon warning"><Icon name="warning" size={26} /></div>
            <h3>{t("admin.link_does_not_work")}</h3>
            <p>{t("admin.link_valid_30_minutes_one")}</p>
          </div>
          <Button className="auth-submit" variant="primary" onClick={onDone}>{t("common.back_sign")}</Button>
        </div>
      </AuthFrame>
    );
  }

  if (status === "done") {
    return (
      <AuthFrame title={t("profile.password_updated")} subtitle={t("admin.can_now_sign_with_new")} logo="shield">
        <div className="auth-card">
          <div className="auth-recovery-sent">
            <div className="auth-recovery-sent-icon success"><Icon name="check" size={26} /></div>
            <h3>{t("common.done")}</h3>
            <p>{t("admin.password_was_changed_sign_chatballs")}</p>
          </div>
          <Button className="auth-submit" variant="primary" onClick={onDone}>{t("admin.sign")}</Button>
        </div>
      </AuthFrame>
    );
  }

  return (
    <AuthFrame title={t("common.new_password")} subtitle={t("admin.set_new_password_sign_chatballs")} logo="shield" width={420} note={backLink}>
      <form className="auth-card" onSubmit={submit}>
        {error && <div className="auth-error"><span className="auth-error-dot">!</span><span>{error}</span></div>}
        <label className="field-label">{t("common.new_password")}</label>
        <AuthField icon="lock" value={password} onChange={setPassword} placeholder={t("common.at_least_10_characters")} type="password" />
        <div className={`password-strength score-${score}`}>
          <div>{[0, 1, 2, 3].map((item) => <span className={item < score ? "active" : ""} key={item} />)}</div>
          <p>{passwordLabels[score]}</p>
        </div>
        <label className="field-label">{t("admin.repeat_password")}</label>
        <AuthField icon="lock" value={confirm} onChange={setConfirm} placeholder={t("common.repeat_new_password")} type="password" error={mismatch} />
        {mismatch && <div className="auth-inline-error">{t("common.passwords_do_not_match")}</div>}
        <div className="password-requirements">
          <strong>{t("common.password_requirements")}</strong>
          <span className={password.length >= 10 ? "done" : ""}>{t("common.at_least_10_characters_long")}</span>
          <span className={/\d/.test(password) ? "done" : ""}>{t("common.contains_digit")}</span>
          <span className={/[A-Za-zА-Яа-я]/.test(password) && /[^A-Za-zА-Яа-я0-9]/.test(password) ? "done" : ""}>{t("common.letters_special_character")}</span>
        </div>
        <Button className="auth-submit" type="submit" variant="primary" disabled={!valid || submitting}>{t("admin.save_sign")}</Button>
      </form>
    </AuthFrame>
  );
}

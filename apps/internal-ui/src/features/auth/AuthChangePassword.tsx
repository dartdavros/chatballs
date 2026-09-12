import { type FormEvent, useState } from "react";

import { api } from "../../api/client";
import type { AuthenticatedUser, SessionUser } from "../../types";
import { Icon } from "../../shared/icons";
import { Button } from "../../shared/ui-controls";
import { AuthField } from "./AuthField";
import { AuthFrame } from "./AuthFrame";
import { passwordIsValid, passwordLabel, passwordScore } from "./password";
import { t } from "../../i18n";

export function AuthChangePassword({ onChanged }: { user: SessionUser; onChanged: (user: AuthenticatedUser) => void }) {
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const score = passwordScore(password);
  const mismatch = confirm.length > 0 && password !== confirm;
  const valid = passwordIsValid(password, mismatch);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!valid) return;
    setSubmitting(true);
    setError("");
    try {
      const payload = await api<{ authenticated: true; user: AuthenticatedUser }>("/api/v1/auth/change-temporary-password/", {
        method: "POST",
        body: JSON.stringify({ newPassword: password }),
      });
      onChanged(payload.user);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : t("admin.could_not_save_password"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthFrame title={t("admin.change_temporary_password")} subtitle={t("admin.signed_with_temporary_password_set")} logo="shield" width={420}>
      <form className="auth-card" onSubmit={submit}>
        {error && <div className="auth-error"><span className="auth-error-dot">!</span><span>{error}</span></div>}
        <label className="field-label">{t("common.new_password")}</label>
        <AuthField icon="lock" value={password} onChange={setPassword} placeholder={t("common.at_least_10_characters")} type="password" />
        <div className={`password-strength score-${score}`}>
          <div>{[0, 1, 2, 3].map((item) => <span className={item < score ? "active" : ""} key={item} />)}</div>
          <p>{passwordLabel(score)}</p>
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

import { type FormEvent, useEffect, useState } from "react";

import { api, ApiError } from "../../api/client";
import { Icon } from "../../shared/icons";
import { Button } from "../../shared/ui-controls";
import { AuthField } from "./AuthField";
import { AuthFrame } from "./AuthFrame";
import { passwordIsValid, passwordLabel, passwordScore } from "./password";
import { t } from "../../i18n";
import type { AuthenticatedUser } from "../../types";

// Ссылка-приглашение без входа (/join?token=…). Сервер говорит, куда зовут и
// есть ли учётная запись: существующая идёт на обычный вход, новая задаёт имя
// и пароль прямо здесь — теми же полями, что в мастере первого запуска, — и
// сразу оказывается в организации.

type Preview = { valid: boolean; email?: string; organizationName?: string; accountExists?: boolean };
type Status = "checking" | "invalid" | "register";
type FieldErrors = { fullName?: string; password?: string };

export function AuthJoinGuest({ token, onUseLogin, onRegistered }: {
  token: string;
  onUseLogin: () => void;
  onRegistered: (user: AuthenticatedUser, organizationPublicId: string) => void;
}) {
  const [status, setStatus] = useState<Status>("checking");
  const [preview, setPreview] = useState<Preview | null>(null);
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let active = true;
    api<Preview>(`/api/v1/auth/invitations/preview/?token=${encodeURIComponent(token)}`)
      .then((payload) => {
        if (!active) return;
        if (!payload.valid) { setStatus("invalid"); return; }
        if (payload.accountExists) { onUseLogin(); return; }
        setPreview(payload);
        setStatus("register");
      })
      .catch(() => { if (active) setStatus("invalid"); });
    return () => { active = false; };
  }, [token, onUseLogin]);

  const score = passwordScore(password);
  const valid = fullName.trim() !== "" && passwordIsValid(password, false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!valid || submitting) return;
    setSubmitting(true);
    setError("");
    setErrors({});
    try {
      const payload = await api<{ user: AuthenticatedUser; organizationPublicId: string }>("/api/v1/auth/invitations/register/", {
        method: "POST",
        body: JSON.stringify({ token, fullName, password }),
      });
      onRegistered(payload.user, payload.organizationPublicId);
    } catch (requestError) {
      if (requestError instanceof ApiError) {
        const fieldErrors = (requestError.payload as { errors?: FieldErrors }).errors;
        if (fieldErrors) setErrors(fieldErrors);
        setError(requestError.message);
      } else {
        setError(t("auth.invitation_not_accepted"));
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (status === "checking") {
    return (
      <AuthFrame title={t("auth.invitation_title")} subtitle={t("admin.one_moment")} logo="shield">
        <div className="auth-card"><p className="auth-hint">{t("admin.checking_link")}</p></div>
      </AuthFrame>
    );
  }

  if (status === "invalid") {
    return (
      <AuthFrame title={t("auth.invitation_title")} subtitle={t("auth.invitation_not_accepted")} logo="shield">
        <div className="auth-card">
          <div className="auth-recovery-sent">
            <div className="auth-recovery-sent-icon warning"><Icon name="warning" size={26} /></div>
            <h3>{t("admin.link_does_not_work")}</h3>
            <p>{t("auth.invitation_invalid")}</p>
          </div>
        </div>
      </AuthFrame>
    );
  }

  return (
    <AuthFrame
      title={t("auth.invitation_title")}
      subtitle={t("auth.join_subtitle", { organization: preview?.organizationName ?? "", email: preview?.email ?? "" })}
      logo="shield"
      width={420}
    >
      <form className="auth-card" onSubmit={submit}>
        {error && <div className="auth-error"><span className="auth-error-dot">!</span><span>{error}</span></div>}
        <label className="field-label">{t("admin.name")}</label>
        <AuthField icon="user" value={fullName} onChange={setFullName} placeholder={t("admin.elena_kuznetsova")} error={Boolean(errors.fullName)} />
        <label className="field-label">{t("common.password")}</label>
        <AuthField icon="lock" value={password} onChange={setPassword} placeholder={t("common.at_least_10_characters")} type={show ? "text" : "password"} error={Boolean(errors.password)}>
          <button type="button" onClick={() => setShow((value) => !value)} aria-label={show ? t("admin.hide_password") : t("admin.show_password")}>
            <Icon name={show ? "eyeOff" : "eye"} size={17} />
          </button>
        </AuthField>
        <div className={`password-strength score-${score}`}>
          <div>{[0, 1, 2, 3].map((item) => <span className={item < score ? "active" : ""} key={item} />)}</div>
          <p>{passwordLabel(score)}</p>
        </div>
        <div className="password-requirements">
          <strong>{t("common.password_requirements")}</strong>
          <span className={password.length >= 10 ? "done" : ""}>{t("common.at_least_10_characters_long")}</span>
          <span className={/\d/.test(password) ? "done" : ""}>{t("common.contains_digit")}</span>
          <span className={/[A-Za-zА-Яа-я]/.test(password) && /[^A-Za-zА-Яа-я0-9]/.test(password) ? "done" : ""}>{t("common.letters_special_character")}</span>
        </div>
        <Button className="auth-submit" type="submit" variant="primary" disabled={!valid || submitting}>{t("auth.join_accept")}</Button>
      </form>
    </AuthFrame>
  );
}

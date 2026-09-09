import { type FormEvent, useState } from "react";

import { api, ApiError } from "../../api/client";
import type { AuthenticatedUser } from "../../types";
import { Icon } from "../../shared/icons";
import { Button } from "../../shared/ui-controls";
import { AuthField } from "./AuthField";
import { AuthFrame } from "./AuthFrame";
import { passwordIsValid, passwordLabels, passwordScore } from "./password";
import { t } from "../../i18n";

type SetupErrors = Partial<Record<"organizationName" | "fullName" | "email" | "password", string>>;

/**
 * Мастер первого запуска: пока в инстансе нет организации, вместо входа —
 * одна форма. Никаких параметров в .env: всё задаёт человек здесь.
 */
export function AuthSetup({ onDone }: { onDone: (user: AuthenticatedUser) => void }) {
  const [organizationName, setOrganizationName] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [installDemo, setInstallDemo] = useState(true);
  const [errors, setErrors] = useState<SetupErrors>({});
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const score = passwordScore(password);
  const valid = organizationName.trim() !== "" && fullName.trim() !== "" && email.trim() !== "" && passwordIsValid(password, false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!valid) return;
    setSubmitting(true);
    setError("");
    setErrors({});
    try {
      const payload = await api<{ authenticated: true; user: AuthenticatedUser }>("/api/v1/setup/complete/", {
        method: "POST",
        body: JSON.stringify({ organizationName, fullName, email, password, installDemo }),
      });
      onDone(payload.user);
    } catch (requestError) {
      if (requestError instanceof ApiError) {
        const fieldErrors = (requestError.payload as { errors?: SetupErrors }).errors;
        if (fieldErrors) setErrors(fieldErrors);
        setError(requestError.message);
      } else {
        setError(t("admin.could_not_create_organization"));
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthFrame title="Chatballs" subtitle={t("admin.first_run_create_organization_owner")} logo="pulse" width={420}>
      <form className="auth-card" onSubmit={submit}>
        {error && <div className="auth-error"><span className="auth-error-dot">!</span><span>{error}</span></div>}
        <label className="field-label">{t("admin.organization_name")}</label>
        <AuthField icon="building" value={organizationName} onChange={setOrganizationName} placeholder={t("admin.nord_atelier")} error={Boolean(errors.organizationName)} />
        <label className="field-label">{t("admin.name")}</label>
        <AuthField icon="user" value={fullName} onChange={setFullName} placeholder={t("admin.elena_kuznetsova")} error={Boolean(errors.fullName)} />
        <label className="field-label">Email</label>
        <AuthField icon="mail" value={email} onChange={setEmail} placeholder="you@domain.ru" error={Boolean(errors.email)} />
        <label className="field-label">{t("common.password")}</label>
        <AuthField icon="lock" value={password} onChange={setPassword} placeholder={t("common.at_least_10_characters")} type={show ? "text" : "password"} error={Boolean(errors.password)}>
          <button type="button" onClick={() => setShow((value) => !value)} aria-label={show ? t("admin.hide_password") : t("admin.show_password")}>
            <Icon name={show ? "eyeOff" : "eye"} size={17} />
          </button>
        </AuthField>
        <div className={`password-strength score-${score}`}>
          <div>{[0, 1, 2, 3].map((item) => <span className={item < score ? "active" : ""} key={item} />)}</div>
          <p>{passwordLabels[score]}</p>
        </div>
        <div className="password-requirements">
          <strong>{t("common.password_requirements")}</strong>
          <span className={password.length >= 10 ? "done" : ""}>{t("common.at_least_10_characters_long")}</span>
          <span className={/\d/.test(password) ? "done" : ""}>{t("common.contains_digit")}</span>
          <span className={/[A-Za-zА-Яа-я]/.test(password) && /[^A-Za-zА-Яа-я0-9]/.test(password) ? "done" : ""}>{t("common.letters_special_character")}</span>
        </div>
        <label className="auth-checkbox">
          <input type="checkbox" checked={installDemo} onChange={(event) => setInstallDemo(event.target.checked)} />
          <span>
            <strong>{t("admin.install_demo_data")}</strong>
            <small>{t("admin.operators_agents_conversations_knowledge_fictional")}</small>
          </span>
        </label>
        <Button className="auth-submit" icon="arrow" iconSize={16} type="submit" variant="primary" disabled={!valid || submitting}>{t("admin.start")}</Button>
      </form>
    </AuthFrame>
  );
}

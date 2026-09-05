import { type FormEvent, useState } from "react";

import { api, ApiError } from "../../api/client";
import type { AuthenticatedUser } from "../../types";
import { Icon } from "../../shared/icons";
import { Button } from "../../shared/ui-controls";
import { AuthField } from "./AuthField";
import { AuthFrame } from "./AuthFrame";
import { passwordIsValid, passwordLabels, passwordScore } from "./password";

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
        setError("Не удалось создать организацию");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthFrame title="Chatballs" subtitle="Первый запуск: создайте организацию и учётную запись владельца" logo="pulse" width={420}>
      <form className="auth-card" onSubmit={submit}>
        {error && <div className="auth-error"><span className="auth-error-dot">!</span><span>{error}</span></div>}
        <label className="field-label">Название организации</label>
        <AuthField icon="building" value={organizationName} onChange={setOrganizationName} placeholder="Ателье Норд" error={Boolean(errors.organizationName)} />
        <label className="field-label">Ваше имя</label>
        <AuthField icon="user" value={fullName} onChange={setFullName} placeholder="Елена Кузнецова" error={Boolean(errors.fullName)} />
        <label className="field-label">Email</label>
        <AuthField icon="mail" value={email} onChange={setEmail} placeholder="you@domain.ru" error={Boolean(errors.email)} />
        <label className="field-label">Пароль</label>
        <AuthField icon="lock" value={password} onChange={setPassword} placeholder="Минимум 10 символов" type={show ? "text" : "password"} error={Boolean(errors.password)}>
          <button type="button" onClick={() => setShow((value) => !value)} aria-label={show ? "Скрыть пароль" : "Показать пароль"}>
            <Icon name={show ? "eyeOff" : "eye"} size={17} />
          </button>
        </AuthField>
        <div className={`password-strength score-${score}`}>
          <div>{[0, 1, 2, 3].map((item) => <span className={item < score ? "active" : ""} key={item} />)}</div>
          <p>{passwordLabels[score]}</p>
        </div>
        <div className="password-requirements">
          <strong>ТРЕБОВАНИЯ К ПАРОЛЮ</strong>
          <span className={password.length >= 10 ? "done" : ""}>Не менее 10 символов</span>
          <span className={/\d/.test(password) ? "done" : ""}>Содержит цифру</span>
          <span className={/[A-Za-zА-Яа-я]/.test(password) && /[^A-Za-zА-Яа-я0-9]/.test(password) ? "done" : ""}>Буквы и спецсимвол</span>
        </div>
        <label className="auth-checkbox">
          <input type="checkbox" checked={installDemo} onChange={(event) => setInstallDemo(event.target.checked)} />
          <span>
            <strong>Установить демо-данные</strong>
            <small>Сотрудники, агенты, диалоги и знания вымышленного ателье — посмотреть систему в работе. Удаляются в «Настройках» одной кнопкой.</small>
          </span>
        </label>
        <Button className="auth-submit" icon="arrow" iconSize={16} type="submit" variant="primary" disabled={!valid || submitting}>Начать</Button>
      </form>
    </AuthFrame>
  );
}

import { type FormEvent, useState } from "react";

import { api } from "../../api/client";
import type { SessionUser } from "../../types";
import { Icon } from "../../shared/icons";
import { Button } from "../../shared/ui-controls";
import { AuthField } from "./AuthField";
import { AuthFrame } from "./AuthFrame";
import { passwordIsValid, passwordLabels, passwordScore } from "./password";

export function AuthChangePassword({ onChanged }: { user: SessionUser; onChanged: (user: SessionUser) => void }) {
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
      const payload = await api<{ authenticated: true; user: SessionUser }>("/api/v1/auth/change-temporary-password/", {
        method: "POST",
        body: JSON.stringify({ newPassword: password }),
      });
      onChanged(payload.user);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Не удалось сохранить пароль");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthFrame title="Смена временного пароля" subtitle="Вы вошли по временному паролю. Задайте постоянный пароль, чтобы продолжить." logo="shield" width={420}>
      <form className="auth-card" onSubmit={submit}>
        {error && <div className="auth-error"><span className="auth-error-dot">!</span><span>{error}</span></div>}
        <label className="field-label">Новый пароль</label>
        <AuthField icon="lock" value={password} onChange={setPassword} placeholder="Минимум 10 символов" type="password" />
        <div className={`password-strength score-${score}`}>
          <div>{[0, 1, 2, 3].map((item) => <span className={item < score ? "active" : ""} key={item} />)}</div>
          <p>{passwordLabels[score]}</p>
        </div>
        <label className="field-label">Повторите пароль</label>
        <AuthField icon="lock" value={confirm} onChange={setConfirm} placeholder="Повторите новый пароль" type="password" error={mismatch} />
        {mismatch && <div className="auth-inline-error">Пароли не совпадают</div>}
        <div className="password-requirements">
          <strong>ТРЕБОВАНИЯ К ПАРОЛЮ</strong>
          <span className={password.length >= 10 ? "done" : ""}>Не менее 10 символов</span>
          <span className={/\d/.test(password) ? "done" : ""}>Содержит цифру</span>
          <span className={/[A-Za-zА-Яа-я]/.test(password) && /[^A-Za-zА-Яа-я0-9]/.test(password) ? "done" : ""}>Буквы и спецсимвол</span>
        </div>
        <Button className="auth-submit" type="submit" variant="primary" disabled={!valid || submitting}>Сохранить и войти</Button>
      </form>
    </AuthFrame>
  );
}

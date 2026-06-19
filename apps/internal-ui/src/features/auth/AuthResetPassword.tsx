import { type FormEvent, useEffect, useState } from "react";

import { api } from "../../api/client";
import { Icon } from "../../shared/icons";
import { Button } from "../../shared/ui-controls";
import { AuthField } from "./AuthField";
import { AuthFrame } from "./AuthFrame";
import { passwordIsValid, passwordLabels, passwordScore } from "./password";

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
      setError(requestError instanceof Error ? requestError.message : "Не удалось сохранить пароль");
    } finally {
      setSubmitting(false);
    }
  }

  const backLink = (
    <button type="button" className="auth-back-login" onClick={onDone}><Icon name="arrow" size={14} />Вернуться ко входу</button>
  );

  if (status === "checking") {
    return (
      <AuthFrame title="Проверяем ссылку" subtitle="Подождите немного." logo="shield">
        <div className="auth-card"><p className="auth-hint">Проверяем ссылку для сброса пароля…</p></div>
      </AuthFrame>
    );
  }

  if (status === "invalid") {
    return (
      <AuthFrame title="Ссылка недействительна" subtitle="Срок действия ссылки истёк или она уже использована." logo="shield" note={backLink}>
        <div className="auth-card">
          <div className="auth-recovery-sent">
            <div className="auth-recovery-sent-icon warning"><Icon name="warning" size={26} /></div>
            <h3>Ссылка не подходит</h3>
            <p>Ссылка действует 30 минут и только один раз. Запросите восстановление доступа ещё раз.</p>
          </div>
          <Button className="auth-submit" variant="primary" onClick={onDone}>Вернуться ко входу</Button>
        </div>
      </AuthFrame>
    );
  }

  if (status === "done") {
    return (
      <AuthFrame title="Пароль обновлён" subtitle="Теперь можно войти с новым паролем." logo="shield">
        <div className="auth-card">
          <div className="auth-recovery-sent">
            <div className="auth-recovery-sent-icon success"><Icon name="check" size={26} /></div>
            <h3>Готово</h3>
            <p>Пароль успешно изменён. Войдите в Hub, используя новый пароль.</p>
          </div>
          <Button className="auth-submit" variant="primary" onClick={onDone}>Войти</Button>
        </div>
      </AuthFrame>
    );
  }

  return (
    <AuthFrame title="Новый пароль" subtitle="Задайте новый пароль для входа в Edevs Hub." logo="shield" width={420} note={backLink}>
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

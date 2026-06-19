import { type FormEvent, useEffect, useRef, useState } from "react";

import { api } from "../../api/client";
import { Icon } from "../../shared/icons";
import { Button } from "../../shared/ui-controls";
import { AuthField } from "./AuthField";
import { AuthFrame } from "./AuthFrame";

const RESEND_COOLDOWN = 30;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function AuthPasswordRecovery({ onBackToLogin }: { onBackToLogin: () => void }) {
  const [step, setStep] = useState<"request" | "sent">("request");
  const [email, setEmail] = useState("");
  const [sentEmail, setSentEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const timer = useRef<number | undefined>(undefined);

  const valid = EMAIL_RE.test(email.trim());

  useEffect(() => () => window.clearInterval(timer.current), []);

  function startCooldown() {
    window.clearInterval(timer.current);
    setCooldown(RESEND_COOLDOWN);
    timer.current = window.setInterval(() => {
      setCooldown((value) => {
        if (value <= 1) {
          window.clearInterval(timer.current);
          return 0;
        }
        return value - 1;
      });
    }, 1000);
  }

  // Ответ сервера одинаков для любого адреса, поэтому UI всегда показывает успех.
  async function sendLink(target: string) {
    setSubmitting(true);
    try {
      await api("/api/v1/auth/password-reset/request/", { method: "POST", body: JSON.stringify({ email: target }) });
    } catch {
      // намеренно игнорируем: не раскрываем результат пользователю
    } finally {
      setSubmitting(false);
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!valid || submitting) return;
    const target = email.trim();
    await sendLink(target);
    setSentEmail(target);
    setStep("sent");
    startCooldown();
  }

  function resend() {
    if (cooldown > 0 || submitting) return;
    void sendLink(sentEmail);
    startCooldown();
  }

  function changeAddress() {
    window.clearInterval(timer.current);
    setCooldown(0);
    setStep("request");
  }

  const backLink = (
    <button type="button" className="auth-back-login" onClick={onBackToLogin}>
      <Icon name="arrow" size={14} />Вернуться ко входу
    </button>
  );

  if (step === "sent") {
    return (
      <AuthFrame title="Письмо отправлено" subtitle="Перейдите по ссылке из письма, чтобы задать новый пароль." logo="pulse" note={backLink}>
        <div className="auth-card">
          <div className="auth-recovery-sent">
            <div className="auth-recovery-sent-icon"><Icon name="mail" size={26} /></div>
            <h3>Проверьте почту</h3>
            <p>Если <b>{sentEmail}</b> зарегистрирован в Hub, на него отправлено письмо со ссылкой для сброса пароля.</p>
          </div>
          <div className="auth-recovery-info">
            <Icon name="clock" size={15} />
            <span>Письмо не пришло за пару минут? Проверьте «Спам» или повторите запрос — ссылка действует 30 минут.</span>
          </div>
          <Button className="auth-submit" variant="primary" onClick={resend} disabled={cooldown > 0 || submitting}>
            {cooldown > 0 ? `Отправить повторно через ${cooldown} с` : "Отправить письмо ещё раз"}
          </Button>
          <Button className="auth-recovery-secondary" variant="secondary" onClick={changeAddress}>Изменить адрес</Button>
        </div>
      </AuthFrame>
    );
  }

  return (
    <AuthFrame title="Восстановление доступа" subtitle="Укажите рабочий email — пришлём ссылку для создания нового пароля." logo="pulse" note={backLink}>
      <form className="auth-card" onSubmit={submit}>
        <label className="field-label">Рабочий email</label>
        <AuthField icon="mail" value={email} onChange={setEmail} placeholder="you@edevs.tech" />
        <p className="auth-recovery-hint">Если адрес зарегистрирован, отправим ссылку для сброса пароля. Ссылка действует 30 минут.</p>
        <Button className="auth-submit" icon="arrow" iconSize={16} type="submit" variant="primary" disabled={!valid || submitting}>Отправить ссылку</Button>
      </form>
    </AuthFrame>
  );
}

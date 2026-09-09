import { type FormEvent, useEffect, useRef, useState } from "react";

import { api } from "../../api/client";
import { Icon } from "../../shared/icons";
import { Button } from "../../shared/ui-controls";
import { AuthField } from "./AuthField";
import { AuthFrame } from "./AuthFrame";
import { t } from "../../i18n";

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
      <Icon name="arrow" size={14} />{t("common.back_sign")}</button>
  );

  if (step === "sent") {
    return (
      <AuthFrame title={t("admin.email_sent")} subtitle={t("admin.follow_link_email_set_new")} logo="pulse" note={backLink}>
        <div className="auth-card">
          <div className="auth-recovery-sent">
            <div className="auth-recovery-sent-icon"><Icon name="mail" size={26} /></div>
            <h3>{t("admin.check_email")}</h3>
            <p>{t("admin.if")}<b>{sentEmail}</b>{t("admin.registered_with_chatballs_email_with")}</p>
          </div>
          <div className="auth-recovery-info">
            <Icon name="clock" size={15} />
            <span>{t("admin.no_email_after_couple_minutes")}</span>
          </div>
          <Button className="auth-submit" variant="primary" onClick={resend} disabled={cooldown > 0 || submitting}>
            {cooldown > 0 ? t("time.resend_in", { seconds: cooldown }) : t("admin.send_email_again")}
          </Button>
          <Button className="auth-recovery-secondary" variant="secondary" onClick={changeAddress}>{t("admin.change_address")}</Button>
        </div>
      </AuthFrame>
    );
  }

  return (
    <AuthFrame title={t("admin.access_recovery")} subtitle={t("admin.enter_work_email_we_will")} logo="pulse" note={backLink}>
      <form className="auth-card" onSubmit={submit}>
        <label className="field-label">{t("admin.work_email_2")}</label>
        <AuthField icon="mail" value={email} onChange={setEmail} placeholder="you@domain.ru" />
        <p className="auth-recovery-hint">{t("admin.if_address_registered_we_will")}</p>
        <Button className="auth-submit" icon="arrow" iconSize={16} type="submit" variant="primary" disabled={!valid || submitting}>{t("admin.send_link")}</Button>
      </form>
    </AuthFrame>
  );
}

import { useEffect, useState, type FormEvent } from "react";

import { FormField, SwitchButton } from "../../shared/form-controls";
import { Button } from "../../shared/ui-controls";
import { shortDateTime } from "../../shared/utils";
import {
  checkInstanceEmail,
  instanceError,
  loadInstance,
  patchInstance,
  type EmailPayload,
  type InstancePayload,
} from "./instance";
import { t } from "../../i18n";

// «Платформа» (Настройки): свойства инсталляции, а не организации. Адрес
// запомнил мастер первого запуска — по нему человек и зашёл, поднимая докер на
// сервере; здесь его меняют, когда завели домен и поставили TLS. Из него
// строятся внешние ссылки: вложения знаний и файлы статей уходят клиенту в
// мессенджер, и «localhost» там мёртв. Почта — соседней карточкой: без неё
// нельзя ни пригласить сотрудника, ни сбросить пароль, а задавать её в
// переменных окружения больше негде. Relay для звонков живёт в «Голосовых и
// звонках» — там же, где включают сами звонки.

type EmailDraft = {
  host: string;
  port: string;
  user: string;
  password: string;
  useTls: boolean;
  from: string;
};

function emailDraftOf(email: EmailPayload): EmailDraft {
  return {
    host: email.host,
    port: String(email.port || 587),
    user: email.user,
    password: "",
    useTls: email.useTls,
    from: email.from,
  };
}

function savedLabel(updatedAt: string | null): string {
  if (!updatedAt) return t("common.never_saved_yet");
  return t("time.saved_at", { time: shortDateTime(updatedAt) });
}

export function PlatformSettingsCard({ canManage }: { canManage: boolean }) {
  const [current, setCurrent] = useState<InstancePayload | null>(null);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    loadInstance()
      .then(setCurrent)
      .catch(() => setLoadError(t("settings.could_not_load_installation_settings")));
  }, []);

  if (loadError) return <div className="settings-section-error">{loadError}</div>;
  if (!current) return null;

  return (
    <>
      <AddressCard canManage={canManage} current={current} onSaved={setCurrent} />
      <LanguageCard canManage={canManage} current={current} onSaved={setCurrent} />
      <EmailCard canManage={canManage} current={current} onSaved={setCurrent} />
    </>
  );
}

// Язык установки — свойство инсталляции, а не организации: на нём открываются
// экраны, где организации ещё нет. Отдельной карточкой рядом с адресом, потому
// что и адрес, и язык здесь — про саму коробку.
function LanguageCard({ canManage, current, onSaved }: {
  canManage: boolean;
  current: InstancePayload;
  onSaved: (payload: InstancePayload) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [errorText, setErrorText] = useState("");

  async function save(language: string) {
    if (language === current.defaultLanguage) return;
    setBusy(true);
    setErrorText("");
    try {
      // Адрес уходит вместе с языком: PATCH проверяет его в любом случае, и
      // без него сохранение языка упало бы на «Укажите адрес установки».
      onSaved(await patchInstance({
        publicHost: current.publicHost,
        publicScheme: current.publicScheme,
        defaultLanguage: language,
      }));
    } catch (error) {
      setErrorText(instanceError(error).detail);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="administration-card">
      <div className="settings-card-head">
        <div>
          <strong>{t("settings.language_instance")}</strong>
          <small>{t("settings.language_instance_hint")}</small>
        </div>
        <div className="appearance-theme-options">
          {current.languages.map((item) => (
            <button
              className={current.defaultLanguage === item.code ? "active" : ""}
              disabled={!canManage || busy}
              key={item.code}
              lang={item.code}
              type="button"
              onClick={() => void save(item.code)}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>
      {errorText && <div className="administration-message error" role="alert">{errorText}</div>}
    </div>
  );
}

function AddressCard({ canManage, current, onSaved }: {
  canManage: boolean;
  current: InstancePayload;
  onSaved: (payload: InstancePayload) => void;
}) {
  const [host, setHost] = useState(current.publicHost);
  const [scheme, setScheme] = useState<"http" | "https">(current.publicScheme);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [errorText, setErrorText] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const touch = () => { setFieldErrors({}); setMessage(""); setErrorText(""); };

  async function save() {
    setBusy(true);
    setMessage("");
    setErrorText("");
    setFieldErrors({});
    try {
      const payload = await patchInstance({ publicHost: host, publicScheme: scheme });
      onSaved(payload);
      setHost(payload.publicHost);
      setScheme(payload.publicScheme);
      setMessage(t("settings.saved_file_links_will_use"));
    } catch (error) {
      const { detail, errors } = instanceError(error);
      setErrorText(detail);
      setFieldErrors(errors);
    } finally {
      setBusy(false);
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void save();
  }

  return (
    <form className="administration-card" onSubmit={submit}>
      <div className="settings-card-head">
        <div>
          <strong>{t("settings.installation_address")}</strong>
          <small>{t("settings.system_opened_at_file_links")}</small>
        </div>
        <div className="appearance-theme-options">
          {(["http", "https"] as const).map((value) => (
            <button
              className={scheme === value ? "active" : ""}
              disabled={!canManage || busy}
              key={value}
              type="button"
              onClick={() => { setScheme(value); touch(); }}
            >
              {value}
            </button>
          ))}
        </div>
      </div>
      <p className="settings-section-note">
        {t("settings.address_hint")} <b>{scheme}://{host || t("settings.address_placeholder")}/…</b>
      </p>
      <div className="administration-fields">
        <FormField
          disabled={!canManage}
          error={fieldErrors.publicHost}
          label={t("settings.domain_or_ip")}
          mono
          placeholder="crm.example.com"
          value={host}
          wide
          onChange={(value) => { setHost(value); touch(); }}
        />
      </div>
      {errorText && <div className="administration-message error" role="alert">{errorText}</div>}
      {canManage && (
        <div className="administration-actions">
          <small className="administration-saved">{message || savedLabel(current.updatedAt)}</small>
          <Button type="submit" variant="primary" disabled={busy || !host.trim()}>
            {busy ? t("common.saving") : t("common.save")}
          </Button>
        </div>
      )}
    </form>
  );
}

function EmailCard({ canManage, current, onSaved }: {
  canManage: boolean;
  current: InstancePayload;
  onSaved: (payload: InstancePayload) => void;
}) {
  const [draft, setDraft] = useState<EmailDraft>(() => emailDraftOf(current.email));
  const [busy, setBusy] = useState<"" | "save" | "check">("");
  const [message, setMessage] = useState("");
  const [errorText, setErrorText] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const touch = () => { setFieldErrors({}); setMessage(""); setErrorText(""); };
  const set = (key: keyof EmailDraft) => (value: string) => { setDraft({ ...draft, [key]: value }); touch(); };

  async function save() {
    setBusy("save");
    setMessage("");
    setErrorText("");
    setFieldErrors({});
    try {
      const payload = await patchInstance({
        email: {
          host: draft.host,
          port: Number(draft.port) || 587,
          user: draft.user,
          password: draft.password,
          useTls: draft.useTls,
          from: draft.from,
        },
      });
      onSaved(payload);
      setDraft(emailDraftOf(payload.email));
      setMessage(t("settings.saved_email_will_go_through"));
    } catch (error) {
      const { detail, errors } = instanceError(error);
      setErrorText(detail);
      setFieldErrors(errors);
    } finally {
      setBusy("");
    }
  }

  async function check() {
    setBusy("check");
    setMessage("");
    setErrorText("");
    try {
      const sent = await checkInstanceEmail();
      setMessage(t("settings.email_sent_to", { email: sent }));
    } catch (error) {
      setErrorText(instanceError(error).detail);
    } finally {
      setBusy("");
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void save();
  }

  return (
    <form className="administration-card" onSubmit={submit}>
      <div className="settings-card-head">
        <div>
          <strong>{t("settings.outgoing_email")}</strong>
          <small>{t("settings.operator_invitations_password_resets")}</small>
        </div>
        {/* Шифрование канала до SMTP — двоичный выбор, значит переключатель
            (тот же стандарт, что у точек входа в «Голосовых и звонках»). */}
        <div className="settings-card-head-switch">
          <span>TLS</span>
          <SwitchButton
            checked={draft.useTls}
            className="ui-switch is-compact"
            disabled={!canManage || Boolean(busy)}
            label={t("settings.tls_encryption_smtp_server")}
            onClick={() => { setDraft({ ...draft, useTls: !draft.useTls }); touch(); }}
          />
        </div>
      </div>
      {!current.email.configured && (
        <p className="settings-section-note">{t("settings.email_not_configured_nothing_sent")}</p>
      )}
      <div className="administration-fields">
        <FormField
          disabled={!canManage}
          error={fieldErrors.emailHost}
          label={t("settings.smtp_server")}
          mono
          placeholder="smtp.example.com"
          value={draft.host}
          onChange={set("host")}
        />
        <FormField
          disabled={!canManage}
          error={fieldErrors.emailPort}
          label={t("settings.port")}
          mono
          placeholder="587"
          value={draft.port}
          onChange={set("port")}
        />
        <FormField
          disabled={!canManage}
          label={t("settings.user")}
          mono
          placeholder="robot@example.com"
          value={draft.user}
          onChange={set("user")}
        />
        <FormField
          disabled={!canManage}
          label={t("common.password")}
          mono
          placeholder={current.email.hasPassword ? t("settings.saved") : ""}
          type="password"
          value={draft.password}
          onChange={set("password")}
        />
        <FormField
          disabled={!canManage}
          label={t("settings.sender")}
          placeholder="Chatballs <no-reply@example.com>"
          value={draft.from}
          wide
          onChange={set("from")}
        />
      </div>
      {errorText && <div className="administration-message error" role="alert">{errorText}</div>}
      {message && <div className="administration-message">{message}</div>}
      {canManage && (
        <div className="administration-actions">
          <small className="administration-saved">{savedLabel(current.updatedAt)}</small>
          {current.email.configured && (
            <Button variant="secondary" disabled={Boolean(busy)} onClick={() => void check()}>
              {busy === "check" ? t("settings.sending") : t("settings.send_test_email")}
            </Button>
          )}
          <Button type="submit" variant="primary" disabled={Boolean(busy)}>
            {busy === "save" ? t("common.saving") : t("common.save")}
          </Button>
        </div>
      )}
    </form>
  );
}

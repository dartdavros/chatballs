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
  if (!updatedAt) return "Ещё не сохранялось";
  return `Сохранено ${shortDateTime(updatedAt)}`;
}

export function PlatformSettingsCard({ canManage }: { canManage: boolean }) {
  const [current, setCurrent] = useState<InstancePayload | null>(null);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    loadInstance()
      .then(setCurrent)
      .catch(() => setLoadError("Не удалось загрузить настройки установки"));
  }, []);

  if (loadError) return <div className="settings-section-error">{loadError}</div>;
  if (!current) return null;

  return (
    <>
      <AddressCard canManage={canManage} current={current} onSaved={setCurrent} />
      <EmailCard canManage={canManage} current={current} onSaved={setCurrent} />
    </>
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
      setMessage("Сохранено. Ссылки на файлы пойдут по этому адресу.");
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
          <strong>Адрес установки</strong>
          <small>По нему открывают систему и по нему строятся ссылки на файлы</small>
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
        Пока домена нет, здесь стоит адрес сервера — тот, на котором вы прошли первый запуск.
        Заведёте домен и поставите перед установкой TLS — впишите его и переключите на https.
        Ссылки будут вида <b>{scheme}://{host || "адрес"}/…</b>
      </p>
      <div className="administration-fields">
        <FormField
          disabled={!canManage}
          error={fieldErrors.publicHost}
          label="Домен или IP"
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
            {busy ? "Сохранение" : "Сохранить"}
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
      setMessage("Сохранено. Письма пойдут через этот сервер.");
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
      setMessage(`Письмо отправлено на ${sent}. Не пришло — проверьте папку «Спам».`);
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
          <strong>Исходящая почта</strong>
          <small>Приглашения сотрудникам и сброс пароля</small>
        </div>
        {/* Шифрование канала до SMTP — двоичный выбор, значит переключатель
            (тот же стандарт, что у точек входа в «Голосовых и звонках»). */}
        <div className="settings-card-head-switch">
          <span>TLS</span>
          <SwitchButton
            checked={draft.useTls}
            className="ui-switch is-compact"
            disabled={!canManage || Boolean(busy)}
            label="Шифрование TLS до SMTP-сервера"
            onClick={() => { setDraft({ ...draft, useTls: !draft.useTls }); touch(); }}
          />
        </div>
      </div>
      {!current.email.configured && (
        <p className="settings-section-note">
          Почта не настроена: письма никуда не уходят, пригласить сотрудника не получится.
        </p>
      )}
      <div className="administration-fields">
        <FormField
          disabled={!canManage}
          error={fieldErrors.emailHost}
          label="SMTP-сервер"
          mono
          placeholder="smtp.example.com"
          value={draft.host}
          onChange={set("host")}
        />
        <FormField
          disabled={!canManage}
          error={fieldErrors.emailPort}
          label="Порт"
          mono
          placeholder="587"
          value={draft.port}
          onChange={set("port")}
        />
        <FormField
          disabled={!canManage}
          label="Пользователь"
          mono
          placeholder="robot@example.com"
          value={draft.user}
          onChange={set("user")}
        />
        <FormField
          disabled={!canManage}
          label="Пароль"
          mono
          placeholder={current.email.hasPassword ? "•••••••• (сохранён)" : ""}
          type="password"
          value={draft.password}
          onChange={set("password")}
        />
        <FormField
          disabled={!canManage}
          label="Отправитель"
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
              {busy === "check" ? "Отправляем…" : "Отправить тестовое письмо"}
            </Button>
          )}
          <Button type="submit" variant="primary" disabled={Boolean(busy)}>
            {busy === "save" ? "Сохранение" : "Сохранить"}
          </Button>
        </div>
      )}
    </form>
  );
}

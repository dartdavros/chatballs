import { useEffect, useState, type FormEvent } from "react";

import { api } from "../../api/client";
import { FormField, TextAreaField } from "../../shared/form-controls";
import { Button } from "../../shared/ui-controls";
import { shortDateTime } from "../../shared/utils";

// «Адрес установки и почта» (Настройки). Адрес запомнил мастер первого запуска —
// по нему человек и зашёл, поднимая докер на сервере; здесь его меняют, когда
// завели домен и поставили TLS. Из него строятся внешние ссылки: вложения знаний
// и файлы статей уходят клиенту в мессенджер, и «localhost» там мёртв.
// Почта — тем же местом: без неё нельзя ни пригласить сотрудника, ни сбросить
// пароль, а задавать её в переменных окружения больше негде.

type EmailPayload = {
  host: string;
  port: number;
  user: string;
  hasPassword: boolean;
  useTls: boolean;
  from: string;
  configured: boolean;
};

type InstancePayload = {
  publicHost: string;
  publicScheme: "http" | "https";
  publicUrl: string;
  updatedAt: string | null;
  email: EmailPayload;
  turn: { urls: string[]; ttlSeconds: number; secretReady: boolean };
};

type EmailDraft = {
  host: string;
  port: string;
  user: string;
  password: string;
  useTls: boolean;
  from: string;
};

const BASE = "/api/v1/company/administration/instance/";

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

function errorMessage(error: unknown): { detail: string; errors: Record<string, string> } {
  if (error && typeof error === "object" && "payload" in error) {
    const payload = (error as { payload?: { detail?: string; errors?: Record<string, string> } }).payload;
    return { detail: payload?.detail ?? "Не удалось сохранить", errors: payload?.errors ?? {} };
  }
  return { detail: error instanceof Error ? error.message : "Не удалось сохранить", errors: {} };
}

export function InstanceAddressCard({ canManage }: { canManage: boolean }) {
  const [current, setCurrent] = useState<InstancePayload | null>(null);
  const [host, setHost] = useState("");
  const [scheme, setScheme] = useState<"http" | "https">("http");
  const [email, setEmail] = useState<EmailDraft | null>(null);
  const [turnUrls, setTurnUrls] = useState("");
  const [turnTtl, setTurnTtl] = useState("3600");
  const [busy, setBusy] = useState<"" | "save" | "check">("");
  const [message, setMessage] = useState("");
  const [errorText, setErrorText] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  function apply(payload: InstancePayload) {
    setCurrent(payload);
    setHost(payload.publicHost);
    setScheme(payload.publicScheme);
    setEmail(emailDraftOf(payload.email));
    setTurnUrls(payload.turn.urls.join("\n"));
    setTurnTtl(String(payload.turn.ttlSeconds || 3600));
  }

  useEffect(() => {
    api<{ instance: InstancePayload }>(BASE)
      .then((payload) => apply(payload.instance))
      .catch(() => setErrorText("Не удалось загрузить настройки установки"));
  }, []);

  if (!current || !email) return null;

  const touch = () => { setFieldErrors({}); setMessage(""); };
  const setEmailField = (key: keyof EmailDraft) => (value: string) => {
    setEmail({ ...email, [key]: value });
    touch();
  };

  async function save() {
    if (!email) return;
    setBusy("save");
    setMessage("");
    setErrorText("");
    setFieldErrors({});
    try {
      const payload = await api<{ instance: InstancePayload }>(BASE, {
        method: "PATCH",
        body: JSON.stringify({
          publicHost: host,
          publicScheme: scheme,
          email: {
            host: email.host,
            port: Number(email.port) || 587,
            user: email.user,
            password: email.password,
            useTls: email.useTls,
            from: email.from,
          },
          turn: {
            urls: turnUrls.split("\n").map((line) => line.trim()).filter(Boolean),
            ttlSeconds: Number(turnTtl) || 3600,
          },
        }),
      });
      apply(payload.instance);
      setMessage("Сохранено. Ссылки и письма пойдут по этим настройкам.");
    } catch (error) {
      const { detail, errors } = errorMessage(error);
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
      const payload = await api<{ sent: string }>(`${BASE}email-check/`, { method: "POST", body: "{}" });
      setMessage(`Письмо отправлено на ${payload.sent}. Не пришло — проверьте папку «Спам».`);
    } catch (error) {
      setErrorText(errorMessage(error).detail);
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
      <div className="settings-storage-head">
        <div>
          <strong>Адрес установки</strong>
          <small>По нему открывают систему и по нему строятся ссылки на файлы</small>
        </div>
        <div className="appearance-theme-options">
          {(["http", "https"] as const).map((value) => (
            <button
              className={scheme === value ? "active" : ""}
              disabled={!canManage || Boolean(busy)}
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
      <p className="settings-section-note">
        Ссылки будут вида <b>{scheme}://{host || "адрес"}/…</b>
      </p>

      <div className="settings-storage-head">
        <div>
          <strong>Исходящая почта</strong>
          <small>Приглашения сотрудникам и сброс пароля</small>
        </div>
        <div className="appearance-theme-options">
          {([[true, "TLS"], [false, "без TLS"]] as Array<[boolean, string]>).map(([value, label]) => (
            <button
              className={email.useTls === value ? "active" : ""}
              disabled={!canManage || Boolean(busy)}
              key={label}
              type="button"
              onClick={() => { setEmail({ ...email, useTls: value }); touch(); }}
            >
              {label}
            </button>
          ))}
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
          value={email.host}
          onChange={setEmailField("host")}
        />
        <FormField
          disabled={!canManage}
          error={fieldErrors.emailPort}
          label="Порт"
          mono
          placeholder="587"
          value={email.port}
          onChange={setEmailField("port")}
        />
        <FormField
          disabled={!canManage}
          label="Пользователь"
          mono
          placeholder="robot@example.com"
          value={email.user}
          onChange={setEmailField("user")}
        />
        <FormField
          disabled={!canManage}
          label="Пароль"
          mono
          placeholder={current.email.hasPassword ? "•••••••• (сохранён)" : ""}
          type="password"
          value={email.password}
          onChange={setEmailField("password")}
        />
        <FormField
          disabled={!canManage}
          label="Отправитель"
          placeholder="Chatballs <no-reply@example.com>"
          value={email.from}
          wide
          onChange={setEmailField("from")}
        />
      </div>

      <div className="settings-storage-head">
        <div>
          <strong>TURN для звонков</strong>
          <small>Relay на случай, когда прямое соединение не проходит</small>
        </div>
      </div>
      <p className="settings-section-note">
        Нужен, только если звонки идут через сети со строгим NAT. Общий секрет с сервером
        relay {current.turn.secretReady ? "уже создан установкой — вводить его не нужно." : "будет создан при следующем запуске стека."}
      </p>
      <div className="administration-fields">
        <TextAreaField
          label="Адреса TURN — по одному в строке"
          value={turnUrls}
          onChange={(value) => { setTurnUrls(value); touch(); }}
        />
        <FormField
          disabled={!canManage}
          error={fieldErrors.turnTtlSeconds}
          label="Время жизни доступа, секунд"
          mono
          value={turnTtl}
          onChange={(value) => { setTurnTtl(value); touch(); }}
        />
      </div>

      {errorText && <div className="administration-message error" role="alert">{errorText}</div>}
      {message && <div className="administration-message">{message}</div>}
      {canManage && (
        <div className="administration-actions">
          <Button variant="primary" disabled={Boolean(busy)} type="submit">
            {busy === "save" ? "Сохраняем…" : "Сохранить"}
          </Button>
          {current.email.configured && (
            <Button variant="secondary" disabled={Boolean(busy)} onClick={() => void check()}>
              {busy === "check" ? "Отправляем…" : "Отправить тестовое письмо"}
            </Button>
          )}
          {current.updatedAt && (
            <span className="settings-section-note">сохранено {shortDateTime(current.updatedAt)}</span>
          )}
        </div>
      )}
    </form>
  );
}

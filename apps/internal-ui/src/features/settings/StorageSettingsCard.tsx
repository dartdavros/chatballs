import { useEffect, useState, type FormEvent } from "react";

import { api } from "../../api/client";
import { FormField, SelectField } from "../../shared/form-controls";
import { Button } from "../../shared/ui-controls";

// «Хранилище файлов» (Настройки): по умолчанию локальный диск установки, по
// желанию — внешнее S3-совместимое хранилище. Секреты не возвращаются с сервера:
// пустое поле при сохранении означает «оставить прежний ключ».

type StorageBackend = "LOCAL" | "S3";

type StoragePayload = {
  backend: StorageBackend;
  s3Bucket: string;
  s3EndpointUrl: string;
  s3Region: string;
  s3AccessKeyMasked: string;
  s3HasSecretKey: boolean;
  s3AddressingStyle: string;
  s3Configured: boolean;
  s3VerifiedAt: string | null;
  s3LastError: string;
  migration: { status: "IDLE" | "RUNNING" | "DONE" | "FAILED"; total: number; done: number; error: string; startedAt: string | null; finishedAt: string | null };
};

type Draft = {
  backend: StorageBackend;
  s3Bucket: string;
  s3EndpointUrl: string;
  s3Region: string;
  s3AccessKey: string;
  s3SecretKey: string;
  s3AddressingStyle: string;
};

const BASE = "/api/v1/company/administration/storage/";

function draftOf(payload: StoragePayload): Draft {
  return {
    backend: payload.backend,
    s3Bucket: payload.s3Bucket,
    s3EndpointUrl: payload.s3EndpointUrl,
    s3Region: payload.s3Region,
    s3AccessKey: "",
    s3SecretKey: "",
    s3AddressingStyle: payload.s3AddressingStyle || "path",
  };
}

function errorMessage(error: unknown): { detail: string; errors: Record<string, string> } {
  if (error && typeof error === "object" && "payload" in error) {
    const payload = (error as { payload?: { detail?: string; errors?: Record<string, string> } }).payload;
    return { detail: payload?.detail ?? "Не удалось сохранить", errors: payload?.errors ?? {} };
  }
  return { detail: error instanceof Error ? error.message : "Не удалось сохранить", errors: {} };
}

export function StorageSettingsCard({ canManage }: { canManage: boolean }) {
  const [current, setCurrent] = useState<StoragePayload | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [busy, setBusy] = useState<"" | "save" | "check" | "migrate">("");
  const [message, setMessage] = useState("");
  const [errorText, setErrorText] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  async function load() {
    const payload = await api<{ storage: StoragePayload }>(BASE);
    setCurrent(payload.storage);
    setDraft((prev) => prev && prev.backend === payload.storage.backend ? prev : draftOf(payload.storage));
    return payload.storage;
  }

  useEffect(() => { void load().catch(() => setErrorText("Не удалось загрузить настройки хранилища")); }, []);

  // Пока идёт перенос — опрашиваем прогресс.
  useEffect(() => {
    if (current?.migration.status !== "RUNNING") return;
    const timer = window.setInterval(() => { void load().catch(() => undefined); }, 3000);
    return () => window.clearInterval(timer);
  }, [current?.migration.status]);

  if (!current || !draft) return null;

  const set = (key: keyof Draft) => (value: string) => { setDraft({ ...draft, [key]: value }); setFieldErrors({}); setMessage(""); };
  const isS3 = draft.backend === "S3";

  async function run(kind: "save" | "check" | "migrate") {
    if (!draft) return;
    setBusy(kind);
    setMessage("");
    setErrorText("");
    setFieldErrors({});
    try {
      if (kind === "save") {
        const payload = await api<{ storage: StoragePayload }>(BASE, { method: "PATCH", body: JSON.stringify(draft) });
        setCurrent(payload.storage);
        setDraft(draftOf(payload.storage));
        setMessage(payload.storage.backend === "S3" ? "Сохранено. Новые файлы пишутся в S3, доступ проверен." : "Сохранено. Файлы хранятся на диске установки.");
      } else if (kind === "check") {
        await api<{ ok: boolean }>(`${BASE}check/`, { method: "POST", body: JSON.stringify(draft) });
        setMessage("Хранилище доступно: пробный объект записан и удалён.");
      } else {
        const payload = await api<{ storage: StoragePayload }>(`${BASE}migrate/`, { method: "POST" });
        setCurrent(payload.storage);
        setMessage("Перенос запущен — идёт в фоне.");
      }
    } catch (error) {
      const { detail, errors } = errorMessage(error);
      setErrorText(detail);
      setFieldErrors(errors);
    } finally {
      setBusy("");
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void run("save");
  }

  const migration = current.migration;
  const migrationLabel = migration.status === "RUNNING"
    ? `Перенос: ${migration.done} из ${migration.total || "…"}`
    : migration.status === "DONE"
      ? `Перенос завершён: ${migration.done} файлов`
      : migration.status === "FAILED"
        ? `Перенос прерван: ${migration.error}`
        : "";

  return (
    <form className="administration-card storage-card" onSubmit={submit}>
      <div className="appearance-row">
        <span>Где хранить файлы</span>
        <div className="appearance-theme-options">
          {([["LOCAL", "На диске установки"], ["S3", "Внешнее S3"]] as Array<[StorageBackend, string]>).map(([value, label]) => (
            <button key={value} type="button" className={draft.backend === value ? "active" : ""} disabled={!canManage || Boolean(busy)} onClick={() => set("backend")(value)}>{label}</button>
          ))}
        </div>
      </div>
      <p className="settings-section-note">
        {isS3
          ? "Вложения знаний, голосовые, фото и логотипы будут записываться в бакет под префиксами организаций. Уже загруженные файлы остаются доступны с диска, пока не перенесены."
          : "Файлы лежат в каталоге data/media установки. Подходит для одного сервера; для нескольких экземпляров или резервирования включите S3."}
      </p>
      {isS3 && (
        <div className="administration-fields storage-fields">
          <FormField label="Бакет" value={draft.s3Bucket} error={fieldErrors.s3Bucket} disabled={!canManage} onChange={set("s3Bucket")} placeholder="chatballs-files" />
          <FormField label="Endpoint (для не-AWS провайдеров)" value={draft.s3EndpointUrl} error={fieldErrors.s3EndpointUrl} disabled={!canManage} onChange={set("s3EndpointUrl")} placeholder="https://storage.example.com" />
          <FormField label="Регион" value={draft.s3Region} error={fieldErrors.s3Region} disabled={!canManage} onChange={set("s3Region")} placeholder="ru-central1" />
          <SelectField label="Адресация" value={draft.s3AddressingStyle} disabled={!canManage} onChange={set("s3AddressingStyle")} options={[["path", "path (bucket в пути)"], ["virtual", "virtual-host (bucket в домене)"]]} />
          <FormField label="Access Key" value={draft.s3AccessKey} error={fieldErrors.s3AccessKey} disabled={!canManage} onChange={set("s3AccessKey")} placeholder={current.s3AccessKeyMasked || "AKIA…"} mono />
          <FormField label="Secret Key" type="password" value={draft.s3SecretKey} error={fieldErrors.s3SecretKey} disabled={!canManage} onChange={set("s3SecretKey")} placeholder={current.s3HasSecretKey ? "•••••••• (сохранён)" : ""} mono />
        </div>
      )}
      {isS3 && current.s3VerifiedAt && !current.s3LastError && (
        <p className="settings-section-note">Доступ проверен {new Date(current.s3VerifiedAt).toLocaleString("ru-RU")}.</p>
      )}
      {migrationLabel && <p className="settings-section-note">{migrationLabel}</p>}
      {errorText && <div className="administration-message error" role="alert">{errorText}</div>}
      {message && <div className="administration-message">{message}</div>}
      {canManage && (
        <div className="administration-actions storage-actions">
          {isS3 && current.backend === "S3" && current.s3Configured && migration.status !== "RUNNING" && (
            <Button variant="secondary" disabled={Boolean(busy)} onClick={() => void run("migrate")}>Перенести файлы с диска в S3</Button>
          )}
          {isS3 && <Button variant="secondary" disabled={Boolean(busy)} onClick={() => void run("check")}>{busy === "check" ? "Проверяем…" : "Проверить доступ"}</Button>}
          <Button type="submit" variant="primary" disabled={Boolean(busy)}>{busy === "save" ? "Сохранение" : "Сохранить"}</Button>
        </div>
      )}
    </form>
  );
}

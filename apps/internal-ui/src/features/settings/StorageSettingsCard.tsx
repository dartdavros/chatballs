import { useEffect, useState, type FormEvent } from "react";

import { api } from "../../api/client";
import { FormField, SelectField } from "../../shared/form-controls";
import { Icon } from "../../shared/icons";
import { shortDateTime } from "../../shared/utils";
import { Button } from "../../shared/ui-controls";
import { fmt, t } from "../../i18n";

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
    return { detail: payload?.detail ?? t("common.could_not_save"), errors: payload?.errors ?? {} };
  }
  return { detail: error instanceof Error ? error.message : t("common.could_not_save"), errors: {} };
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

  useEffect(() => { void load().catch(() => setErrorText(t("settings.could_not_load_storage_settings"))); }, []);

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
        setMessage(payload.storage.backend === "S3" ? t("settings.saved_new_files_go_s3") : t("settings.saved_files_kept_installation_disk"));
      } else if (kind === "check") {
        await api<{ ok: boolean }>(`${BASE}check/`, { method: "POST", body: JSON.stringify(draft) });
        setMessage(t("settings.storage_reachable_test_object_was"));
      } else {
        const payload = await api<{ storage: StoragePayload }>(`${BASE}migrate/`, { method: "POST" });
        setCurrent(payload.storage);
        setMessage(t("settings.migration_has_started_runs_background"));
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
    ? t("settings.migration_progress", { done: migration.done, total: migration.total || "…" })
    : migration.status === "DONE"
      ? t("settings.migration_done", { done: migration.done })
      : migration.status === "FAILED"
        ? t("settings.migration_failed", { error: migration.error })
        : "";

  return (
    <form className="administration-card storage-card" onSubmit={submit}>
      <div className="settings-card-head">
        <div>
          <strong>{t("settings.where_keep_files")}</strong>
          <small>{t("settings.knowledge_attachments_voice_messages_photos")}</small>
        </div>
        <div className="appearance-theme-options">
          {([["LOCAL", t("settings.installation_disk")], ["S3", t("settings.external_s3")]] as Array<[StorageBackend, string]>).map(([value, label]) => (
            <button key={value} type="button" className={draft.backend === value ? "active" : ""} disabled={!canManage || Boolean(busy)} onClick={() => set("backend")(value)}>{label}</button>
          ))}
        </div>
      </div>
      <p className="settings-section-note">
        {isS3
          ? t("settings.knowledge_attachments_voice_messages_photos_2")
          : t("settings.files_live_installation_s_data")}
      </p>
      {isS3 && (
        <div className="administration-fields storage-fields">
          <FormField label={t("settings.bucket")} value={draft.s3Bucket} error={fieldErrors.s3Bucket} disabled={!canManage} onChange={set("s3Bucket")} placeholder="chatballs-files" />
          <FormField label={t("settings.region")} value={draft.s3Region} error={fieldErrors.s3Region} disabled={!canManage} onChange={set("s3Region")} placeholder="ru-central1" />
          <FormField label={t("settings.endpoint_non_aws_providers")} value={draft.s3EndpointUrl} error={fieldErrors.s3EndpointUrl} disabled={!canManage} onChange={set("s3EndpointUrl")} placeholder="https://storage.example.com" wide />
          <SelectField label={t("settings.addressing")} value={draft.s3AddressingStyle} disabled={!canManage} onChange={set("s3AddressingStyle")} options={[["path", t("settings.path_bucket_path")], ["virtual", t("settings.virtual_host_bucket_domain")]]} />
          <FormField label="Access Key" value={draft.s3AccessKey} error={fieldErrors.s3AccessKey} disabled={!canManage} onChange={set("s3AccessKey")} placeholder={current.s3AccessKeyMasked || "AKIA…"} mono />
          <FormField label="Secret Key" type="password" value={draft.s3SecretKey} error={fieldErrors.s3SecretKey} disabled={!canManage} onChange={set("s3SecretKey")} placeholder={current.s3HasSecretKey ? t("settings.saved") : ""} mono />
        </div>
      )}
      {isS3 && current.s3VerifiedAt && !current.s3LastError && (
        <div className="settings-storage-status">
          <Icon name="check" size={15} />
          <span>{t("settings.access_checked_at", { date: shortDateTime(current.s3VerifiedAt) })}{migrationLabel ? ` · ${migrationLabel.toLocaleLowerCase(fmt.tag())}` : ""}</span>
        </div>
      )}
      {migrationLabel && (!isS3 || !current.s3VerifiedAt || Boolean(current.s3LastError)) && <p className="settings-section-note">{migrationLabel}</p>}
      {errorText && <div className="administration-message error" role="alert">{errorText}</div>}
      {message && <div className="administration-message">{message}</div>}
      {canManage && (
        <div className="administration-actions storage-actions">
          {isS3 && current.backend === "S3" && current.s3Configured && migration.status !== "RUNNING" && (
            <Button variant="secondary" disabled={Boolean(busy)} onClick={() => void run("migrate")}>{t("settings.migrate_files_from_disk")}</Button>
          )}
          {isS3 && <Button variant="secondary" disabled={Boolean(busy)} onClick={() => void run("check")}>{busy === "check" ? t("settings.checking") : t("settings.check_access")}</Button>}
          <Button type="submit" variant="primary" disabled={Boolean(busy)}>{busy === "save" ? t("common.saving") : t("common.save")}</Button>
        </div>
      )}
    </form>
  );
}

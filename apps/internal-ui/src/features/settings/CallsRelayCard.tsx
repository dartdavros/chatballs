import { useEffect, useState, type FormEvent } from "react";

import { FormField, TextAreaField } from "../../shared/form-controls";
import { Button } from "../../shared/ui-controls";
import { shortDateTime } from "../../shared/utils";
import { instanceError, loadInstance, patchInstance, type InstancePayload } from "./instance";
import { t } from "../../i18n";

// Relay для звонков (раздел «Голосовые и звонки»): TURN нужен, только когда
// прямое ICE-соединение не проходит — сети со строгим NAT. Настройка живёт
// рядом с выключателями самих звонков, а не в «Организации»: включать звонки и
// чинить их прохождение — одна задача. Общий секрет с coturn лежит в томе
// секретов и наружу не отдаётся — вводить его человеку не нужно.

export function CallsRelayCard({ canManage }: { canManage: boolean }) {
  const [current, setCurrent] = useState<InstancePayload | null>(null);
  const [urls, setUrls] = useState("");
  const [ttl, setTtl] = useState("3600");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [errorText, setErrorText] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  function apply(payload: InstancePayload) {
    setCurrent(payload);
    setUrls(payload.turn.urls.join("\n"));
    setTtl(String(payload.turn.ttlSeconds || 3600));
  }

  useEffect(() => {
    loadInstance().then(apply).catch(() => setErrorText(t("settings.could_not_load_relay_settings")));
  }, []);

  if (!current) return null;

  const touch = () => { setFieldErrors({}); setMessage(""); setErrorText(""); };

  async function save() {
    setBusy(true);
    setMessage("");
    setErrorText("");
    setFieldErrors({});
    try {
      const payload = await patchInstance({
        turn: {
          urls: urls.split("\n").map((line) => line.trim()).filter(Boolean),
          ttlSeconds: Number(ttl) || 3600,
        },
      });
      apply(payload);
      setMessage(t("settings.saved_calls_will_use_these"));
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
          <strong>{t("settings.turn_calls")}</strong>
          <small>{t("settings.relay_when_direct_connection_does")}</small>
        </div>
      </div>
      <p className="settings-section-note">
        {t("settings.turn_note_prefix")} {current.turn.secretReady
          ? t("settings.was_already_created_by_installation")
          : t("settings.will_created_next_time_stack")}
      </p>
      <div className="administration-fields">
        <TextAreaField
          disabled={!canManage}
          label={t("settings.turn_addresses_one_per_line")}
          value={urls}
          onChange={(value) => { setUrls(value); touch(); }}
        />
        <FormField
          disabled={!canManage}
          error={fieldErrors.turnTtlSeconds}
          label={t("settings.access_lifetime_seconds")}
          mono
          value={ttl}
          onChange={(value) => { setTtl(value); touch(); }}
        />
      </div>
      {errorText && <div className="administration-message error" role="alert">{errorText}</div>}
      {message && <div className="administration-message">{message}</div>}
      {canManage && (
        <div className="administration-actions">
          <small className="administration-saved">
            {current.updatedAt ? t("time.saved_at", { time: shortDateTime(current.updatedAt) }) : t("common.never_saved_yet")}
          </small>
          <Button type="submit" variant="primary" disabled={busy}>
            {busy ? t("common.saving") : t("common.save")}
          </Button>
        </div>
      )}
    </form>
  );
}

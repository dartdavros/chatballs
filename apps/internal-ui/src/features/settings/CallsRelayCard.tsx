import { useEffect, useState, type FormEvent } from "react";

import { FormField, TextAreaField } from "../../shared/form-controls";
import { Button } from "../../shared/ui-controls";
import { shortDateTime } from "../../shared/utils";
import { instanceError, loadInstance, patchInstance, type InstancePayload } from "./instance";

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
    loadInstance().then(apply).catch(() => setErrorText("Не удалось загрузить настройки relay"));
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
      setMessage("Сохранено. Звонки будут использовать эти адреса relay.");
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
          <strong>TURN для звонков</strong>
          <small>Relay на случай, когда прямое соединение не проходит</small>
        </div>
      </div>
      <p className="settings-section-note">
        Нужен, только если звонки идут через сети со строгим NAT. Общий секрет с сервером
        relay {current.turn.secretReady
          ? "уже создан установкой — вводить его не нужно."
          : "будет создан при следующем запуске стека."}
      </p>
      <div className="administration-fields">
        <TextAreaField
          disabled={!canManage}
          label="Адреса TURN — по одному в строке"
          value={urls}
          onChange={(value) => { setUrls(value); touch(); }}
        />
        <FormField
          disabled={!canManage}
          error={fieldErrors.turnTtlSeconds}
          label="Время жизни доступа, секунд"
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
            {current.updatedAt ? `Сохранено ${shortDateTime(current.updatedAt)}` : "Ещё не сохранялось"}
          </small>
          <Button type="submit" variant="primary" disabled={busy}>
            {busy ? "Сохранение" : "Сохранить"}
          </Button>
        </div>
      )}
    </form>
  );
}

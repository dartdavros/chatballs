import { useEffect, useState } from "react";

import { api } from "../../api/client";
import { ChannelGlyph } from "../../shared/badges";
import { SwitchButton } from "../../shared/form-controls";

// «Голосовые и звонки» (Настройки): матрица точек входа × функции. Что
// разрешено клиенту и сотруднику в диалогах через каждую интеграцию —
// голосовые сообщения, аудио- и видеозвонки. Почта звонки не поддерживает.

type EntryPoint = {
  id: number;
  name: string;
  provider: string;
  isActive: boolean;
  agentName: string;
  supportsCalls: boolean;
  voiceMessages: boolean;
  audioCalls: boolean;
  videoCalls: boolean;
};

type Flag = "voiceMessages" | "audioCalls" | "videoCalls";

const BASE = "/api/v1/company/administration/communication/";
const COLUMNS: Array<[Flag, string]> = [["voiceMessages", "Голосовые"], ["audioCalls", "Аудиозвонки"], ["videoCalls", "Видеозвонки"]];

export function CommunicationSettingsCard({ canManage }: { canManage: boolean }) {
  const [items, setItems] = useState<EntryPoint[] | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [errorText, setErrorText] = useState("");

  useEffect(() => {
    api<{ items: EntryPoint[] }>(BASE).then((payload) => setItems(payload.items)).catch(() => setErrorText("Не удалось загрузить точки входа"));
  }, []);

  if (!items) return null;

  async function toggle(item: EntryPoint, flag: Flag) {
    if (!canManage || busyId != null) return;
    setBusyId(item.id);
    setErrorText("");
    try {
      const payload = await api<{ items: EntryPoint[] }>(BASE, { method: "PATCH", body: JSON.stringify({ items: [{ id: item.id, [flag]: !item[flag] }] }) });
      setItems(payload.items);
    } catch (error) {
      setErrorText(error instanceof Error ? error.message : "Не удалось сохранить");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="profile-card">
      <p className="settings-section-note">Клиент и сотрудник могут записывать голосовые и начинать звонки только там, где это разрешено. Голосовые, присланные клиентом из мессенджера, принимаются всегда.</p>
      {items.length === 0 && <p className="settings-section-note">Точек входа пока нет — подключите бота, почту или Web-виджет в «Интеграциях».</p>}
      {items.length > 0 && (
        <div className="communication-matrix">
          <div className="communication-row is-head">
            <span>Точка входа</span>
            {COLUMNS.map(([flag, label]) => <span key={flag}>{label}</span>)}
          </div>
          {items.map((item) => (
            <div className={`communication-row${item.isActive ? "" : " is-inactive"}`} key={item.id}>
              <span className="communication-entry">
                <ChannelGlyph provider={item.provider} size={14} />
                <strong>{item.name}</strong>
                <small>{item.agentName || "без агента"}{item.isActive ? "" : " · выключена"}</small>
              </span>
              {COLUMNS.map(([flag, label]) => (
                <span key={flag}>
                  {flag === "voiceMessages" || item.supportsCalls
                    ? <SwitchButton checked={item[flag]} className="ui-switch" label={`${label}: ${item.name}`} disabled={!canManage || busyId != null} onClick={() => void toggle(item, flag)} />
                    : <small className="communication-na">недоступно</small>}
                </span>
              ))}
            </div>
          ))}
        </div>
      )}
      {errorText && <div className="settings-section-error">{errorText}</div>}
    </div>
  );
}

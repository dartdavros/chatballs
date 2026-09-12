import { useEffect, useState } from "react";

import { api } from "../../api/client";
import { ChannelGlyph } from "../../shared/badges";
import { SwitchButton } from "../../shared/form-controls";
import { CallsRelayCard } from "./CallsRelayCard";
import { t } from "../../i18n";

// «Голосовые и звонки» (Настройки): матрица точек входа × функции. Что
// разрешено клиенту и сотруднику в диалогах через каждую интеграцию —
// голосовые сообщения, аудио- и видеозвонки. Почта звонки не поддерживает.
// Ниже матрицы — relay TURN: включать звонки и чинить их прохождение через
// строгий NAT это одна задача, поэтому настройка живёт здесь же.

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
const COLUMNS: Array<[Flag, string]> = [["voiceMessages", t("settings.voice_messages")], ["audioCalls", t("settings.audio_calls")], ["videoCalls", t("settings.video_calls")]];

// Relay — настройка установки, а не организации: менять его может только
// администратор установки, поэтому право приходит отдельным флагом.
export function CommunicationSettingsCard({ canManage, canManageRelay }: { canManage: boolean; canManageRelay: boolean }) {
  const [items, setItems] = useState<EntryPoint[] | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [errorText, setErrorText] = useState("");

  useEffect(() => {
    api<{ items: EntryPoint[] }>(BASE).then((payload) => setItems(payload.items)).catch(() => setErrorText(t("settings.could_not_load_entry_points")));
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
      setErrorText(error instanceof Error ? error.message : t("common.could_not_save"));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <>
      {items.length === 0 && <p className="settings-section-note">{t("settings.there_no_entry_points_yet")}</p>}
      {items.length > 0 && (
        <div className="table-card communication-matrix">
          <div className="communication-row is-head">
            <span>{t("settings.entry_point")}</span>
            {COLUMNS.map(([flag, label]) => <span key={flag}>{label}</span>)}
          </div>
          {items.map((item) => (
            <div className={`communication-row${item.isActive ? "" : " is-inactive"}`} key={item.id}>
              <span className="communication-entry">
                <ChannelGlyph provider={item.provider} size={16} />
                <strong>{item.name}</strong>
                <small>{item.agentName || t("settings.no_agent")}{item.isActive ? "" : t("settings.entry_point_off")}</small>
              </span>
              {COLUMNS.map(([flag, label]) => (
                <span key={flag}>
                  {flag === "voiceMessages" || item.supportsCalls
                    ? <SwitchButton checked={item[flag]} className="ui-switch is-compact" label={`${label}: ${item.name}`} disabled={!canManage || busyId != null} onClick={() => void toggle(item, flag)} />
                    : <small className="communication-na">{t("settings.unavailable")}</small>}
                </span>
              ))}
            </div>
          ))}
        </div>
      )}
      {errorText && <div className="settings-section-error">{errorText}</div>}
      {items.length > 0 && (
        <p className="settings-section-note">{t("settings.voice_messages_sent_by_customer")}</p>
      )}
      <CallsRelayCard canManage={canManageRelay} />
    </>
  );
}

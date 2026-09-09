import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "../../api/client";
import { Icon, LogoSpinner, MaxLogo, TelegramLogo } from "../../shared/icons";
import { Button } from "../../shared/ui-controls";
import { t } from "../../i18n";

// «Уведомления в мессенджер» (дизайн-базлайн v2, кадр P1): по строке на бота —
// фирменная плитка, статус привязки и типы событий галочками (ADR-0015).
// Мессенджер один: привязка нового заменяет текущий.

type BindingItem = { integrationId: number; provider: "TELEGRAM" | "MAX"; name: string; botUsername: string; bound: boolean; pushTypes: string[] };
type TypeOption = { code: string; label: string };
type BindingsResponse = { items: BindingItem[]; availableTypes: TypeOption[] };

const PROVIDER_LABEL: Record<BindingItem["provider"], string> = { TELEGRAM: "Telegram", MAX: "MAX" };
const PROVIDER_TILE: Record<BindingItem["provider"], string> = { TELEGRAM: "integration-tile--telegram", MAX: "integration-tile--max" };

const fetchBindings = () => api<BindingsResponse>("/api/v1/notifications/messenger-bindings/");

export function ProfileNotificationsCard() {
  const [items, setItems] = useState<BindingItem[]>([]);
  const [types, setTypes] = useState<TypeOption[]>([]);
  const [loaded, setLoaded] = useState(false);
  // Диплинки выдаются заранее для всех непривязанных ботов — кнопка «Привязать
  // бота» становится обычной ссылкой (без промежуточных шагов и popup-блокеров).
  const [links, setLinks] = useState<Record<number, { deepLink: string; code: string }>>({});
  const [busy, setBusy] = useState(false);
  const issuedFor = useRef<Set<number>>(new Set());

  const reload = useCallback(async () => {
    try {
      const data = await fetchBindings();
      setItems(data.items);
      setTypes(data.availableTypes);
      for (const item of data.items) {
        if (item.bound || issuedFor.current.has(item.integrationId)) continue;
        issuedFor.current.add(item.integrationId);
        api<{ code: string; deepLink: string }>(`/api/v1/notifications/messenger-bindings/${item.integrationId}/`, { method: "POST" })
          .then((issued) => setLinks((prev) => ({ ...prev, [item.integrationId]: { deepLink: issued.deepLink, code: issued.code } })))
          .catch(() => issuedFor.current.delete(item.integrationId));
      }
    } catch {
      /* ignore */
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  // Пока есть непривязанные боты — ждём подтверждения из мессенджера.
  const hasUnbound = items.some((item) => !item.bound);
  useEffect(() => {
    if (!hasUnbound) return;
    const timer = window.setInterval(() => {
      fetchBindings().then((data) => { setItems(data.items); setTypes(data.availableTypes); }).catch(() => undefined);
    }, 3000);
    return () => window.clearInterval(timer);
  }, [hasUnbound]);

  async function disconnect(item: BindingItem) {
    setBusy(true);
    try {
      await api(`/api/v1/notifications/messenger-bindings/${item.integrationId}/`, { method: "DELETE" });
      issuedFor.current.delete(item.integrationId);
      await reload();
    } catch {
      /* ignore */
    } finally {
      setBusy(false);
    }
  }

  async function toggleType(item: BindingItem, code: string) {
    const next = item.pushTypes.includes(code) ? item.pushTypes.filter((t) => t !== code) : [...item.pushTypes, code];
    setItems((prev) => prev.map((row) => (row.integrationId === item.integrationId ? { ...row, pushTypes: next } : row)));
    await api(`/api/v1/notifications/messenger-bindings/${item.integrationId}/`, { method: "PATCH", body: JSON.stringify({ pushTypes: next }) }).catch(() => undefined);
  }

  return (
    <section className="profile-card">
      <h3>{t("profile.messenger_notifications")}</h3>
      <p className="profile-card-lead">{t("profile.work_events_reach_even_with")}</p>
      {loaded && items.length === 0 && (
        <p className="profile-notifications-note">{t("profile.no_notification_bots_configured_owner")}</p>
      )}
      {items.map((item) => (
        <div className="profile-notifications-block" key={item.integrationId}>
          <div className="profile-notifications-row">
            <span className={`profile-notifications-tile integration-tile ${PROVIDER_TILE[item.provider]}`}>
              {item.provider === "TELEGRAM" ? <TelegramLogo size={19} /> : <MaxLogo size={19} />}
            </span>
            <div className="profile-notifications-name">
              <strong>{PROVIDER_LABEL[item.provider] ?? item.provider}</strong>
              <small>{item.botUsername ? t("profile.service_notification_bot", { username: item.botUsername }) : item.name}</small>
            </div>
            {item.bound ? (
              <>
                <b className="profile-notifications-status">{t("common.connected")}</b>
                <Button variant="secondary" disabled={busy} onClick={() => void disconnect(item)}>{t("profile.disconnect")}</Button>
              </>
            ) : links[item.integrationId]?.deepLink ? (
              <a className="profile-notifications-bind" href={links[item.integrationId].deepLink} target="_blank" rel="noreferrer">{t("profile.link_bot")}<Icon name="external" size={12} strokeWidth={2.2} />
              </a>
            ) : (
              <span className="profile-notifications-wait">{loaded ? t("profile.preparing_link") : <LogoSpinner size={16} />}</span>
            )}
          </div>
          {item.bound && types.length > 0 && (
            <div className="profile-notifications-types">
              {types.map((type) => {
                const on = item.pushTypes.includes(type.code);
                return (
                  <label key={type.code}>
                    <input type="checkbox" checked={on} onChange={() => void toggleType(item, type.code)} />
                    <span className={`profile-check ${on ? "is-on" : ""}`}>{on && <Icon name="check" size={11} strokeWidth={3} />}</span>
                    {type.label}
                  </label>
                );
              })}
            </div>
          )}
        </div>
      ))}
      {hasUnbound && (
        <p className="profile-notifications-note">{t("profile.press_link_bot_then_start")}</p>
      )}
    </section>
  );
}

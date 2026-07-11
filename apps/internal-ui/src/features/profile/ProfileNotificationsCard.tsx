import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "../../api/client";
import { Button } from "../../shared/ui-controls";

type BindingItem = { integrationId: number; provider: "TELEGRAM" | "MAX"; name: string; botUsername: string; bound: boolean; pushTypes: string[] };
type TypeOption = { code: string; label: string };
type BindingsResponse = { items: BindingItem[]; availableTypes: TypeOption[] };

const PROVIDER_LABEL: Record<BindingItem["provider"], string> = { TELEGRAM: "Telegram", MAX: "MAX" };

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
      <h3>Уведомления в мессенджер</h3>
      {loaded && items.length === 0 && (
        <p className="profile-notifications-note">Боты уведомлений не настроены. Владелец может добавить бота в разделе «Интеграции» (флажок «Бот уведомлений для сотрудников»).</p>
      )}
      {items.map((item) => (
        <div className="profile-notifications-block" key={item.integrationId}>
          <div className="profile-notifications-row">
            <div>
              <strong>{PROVIDER_LABEL[item.provider] ?? item.provider}</strong>
              <small>{item.botUsername ? `@${item.botUsername}` : item.name}</small>
            </div>
            {item.bound ? (
              <div className="profile-notifications-actions">
                <span className="profile-notifications-status ok">Подключено</span>
                <Button variant="secondary" disabled={busy} onClick={() => void disconnect(item)}>Отключить</Button>
              </div>
            ) : links[item.integrationId]?.deepLink ? (
              <a className="profile-notifications-bind" href={links[item.integrationId].deepLink} target="_blank" rel="noreferrer">Привязать бота</a>
            ) : (
              <span className="profile-notifications-status wait">{loaded ? "Готовим ссылку…" : "Загрузка…"}</span>
            )}
          </div>
          {item.bound && types.length > 0 && (
            <div className="profile-notifications-types">
              {types.map((type) => (
                <label key={type.code}>
                  <input type="checkbox" checked={item.pushTypes.includes(type.code)} onChange={() => void toggleType(item, type.code)} />
                  {type.label}
                </label>
              ))}
            </div>
          )}
        </div>
      ))}
      {hasUnbound && (
        <p className="profile-notifications-note">Нажмите «Привязать бота» и в открывшемся чате нажмите «Начать» — привязка подтвердится автоматически. Уведомления приходят в один мессенджер: привязка нового заменяет текущий.</p>
      )}
    </section>
  );
}

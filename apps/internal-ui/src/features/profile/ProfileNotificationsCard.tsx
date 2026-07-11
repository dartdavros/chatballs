import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "../../api/client";
import { Button } from "../../shared/ui-controls";

type BindingItem = { integrationId: number; provider: "TELEGRAM" | "MAX"; name: string; botUsername: string; bound: boolean };
type IssuedCode = { integrationId: number; code: string; deepLink: string };

const PROVIDER_LABEL: Record<BindingItem["provider"], string> = { TELEGRAM: "Telegram", MAX: "MAX" };

const fetchBindings = () => api<{ items: BindingItem[] }>("/api/v1/notifications/messenger-bindings/").then((r) => r.items);

export function ProfileNotificationsCard() {
  const [items, setItems] = useState<BindingItem[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [issued, setIssued] = useState<IssuedCode | null>(null);
  const [busy, setBusy] = useState(false);
  const pollTimer = useRef<number | null>(null);

  const reload = useCallback(async () => {
    try {
      setItems(await fetchBindings());
    } catch {
      /* ignore */
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => {
    void reload();
    return () => {
      if (pollTimer.current !== null) window.clearInterval(pollTimer.current);
    };
  }, [reload]);

  // Пока показан код привязки — ждём подтверждения от бота (поллинг статуса).
  useEffect(() => {
    if (issued === null) return;
    pollTimer.current = window.setInterval(async () => {
      const fresh = await fetchBindings().catch(() => null);
      if (!fresh) return;
      setItems(fresh);
      if (fresh.find((item) => item.integrationId === issued.integrationId)?.bound) setIssued(null);
    }, 3000);
    return () => {
      if (pollTimer.current !== null) window.clearInterval(pollTimer.current);
    };
  }, [issued]);

  async function connect(item: BindingItem) {
    setBusy(true);
    try {
      const result = await api<{ code: string; deepLink: string }>(`/api/v1/notifications/messenger-bindings/${item.integrationId}/`, { method: "POST" });
      setIssued({ integrationId: item.integrationId, code: result.code, deepLink: result.deepLink });
    } catch {
      /* ignore */
    } finally {
      setBusy(false);
    }
  }

  async function disconnect(item: BindingItem) {
    setBusy(true);
    try {
      await api(`/api/v1/notifications/messenger-bindings/${item.integrationId}/`, { method: "DELETE" });
      setIssued(null);
      await reload();
    } catch {
      /* ignore */
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="profile-card">
      <h3>Уведомления в мессенджер</h3>
      <p className="profile-notifications-note">Новые диалоги и сообщения будут приходить вам от сервисного бота.</p>
      {loaded && items.length === 0 && (
        <p className="profile-notifications-note">Боты уведомлений не настроены. Владелец может добавить бота в разделе «Интеграции» (флажок «Бот уведомлений для сотрудников»).</p>
      )}
      {items.map((item) => (
        <div className="profile-notifications-row" key={item.integrationId}>
          <div>
            <strong>{PROVIDER_LABEL[item.provider] ?? item.provider}</strong>
            <small>{item.botUsername ? `@${item.botUsername}` : item.name}</small>
          </div>
          {item.bound ? (
            <div className="profile-notifications-actions">
              <span className="profile-notifications-status ok">Подключено</span>
              <Button variant="secondary" disabled={busy} onClick={() => void disconnect(item)}>Отключить</Button>
            </div>
          ) : issued?.integrationId === item.integrationId ? (
            <div className="profile-notifications-actions">
              <span className="profile-notifications-status wait">Ожидание подтверждения…</span>
              {issued.deepLink && (
                <a className="profile-notifications-link" href={issued.deepLink} target="_blank" rel="noreferrer">Открыть бота</a>
              )}
              <code>{issued.code}</code>
            </div>
          ) : (
            <Button variant="secondary" disabled={busy} onClick={() => void connect(item)}>Подключить</Button>
          )}
        </div>
      ))}
      {issued !== null && (
        <p className="profile-notifications-note">Перейдите по ссылке и нажмите «Старт» — либо отправьте боту код вручную. Код действует 10 минут.</p>
      )}
    </section>
  );
}

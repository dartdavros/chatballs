import { useCallback, useEffect, useState } from "react";

import { Icon } from "../../shared/icons";
import { Button } from "../../shared/ui-controls";
import { fetchProfileSessions, lastSeenLabel, type ProfileSession } from "./model";

// «Активные сессии» (дизайн-базлайн v2, кадр P1): устройство, частично скрытый
// адрес и когда сессия была активна; текущая помечена бейджем.

const KIND_ICON: Record<ProfileSession["kind"], Parameters<typeof Icon>[0]["name"]> = {
  laptop: "laptop",
  phone: "smartphone",
  monitor: "monitor",
};

export function ProfileSessionsCard({ message, revoking, onRevoke }: { message: string; revoking: boolean; onRevoke: () => void }) {
  const [items, setItems] = useState<ProfileSession[]>([]);

  const load = useCallback(() => {
    fetchProfileSessions().then(setItems).catch(() => undefined);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // После «Завершить другие» список перечитываем.
  useEffect(() => {
    if (!revoking) load();
  }, [load, revoking]);

  return (
    <section className="profile-card sessions-card">
      <div className="sessions-head">
        <h3>Активные сессии</h3>
        <Button className="sessions-revoke" type="button" variant="danger-outline" onClick={onRevoke} disabled={revoking || items.length < 2}>
          {revoking ? "Завершение" : "Завершить другие"}
        </Button>
      </div>
      {message && <div className="profile-message sessions">{message}</div>}
      {items.map((session) => {
        const seen = lastSeenLabel(session.lastSeenAt);
        const where = [session.address, session.current ? seen : ""].filter(Boolean).join(" · ");
        return (
          <div className="session-row" key={session.id}>
            <span className="session-icon"><Icon name={KIND_ICON[session.kind]} size={16} strokeWidth={1.9} /></span>
            <span className="session-main">
              <strong>{session.device}</strong>
              <small>{where || "адрес неизвестен"}</small>
            </span>
            {session.current ? <b className="session-current">текущая</b> : <small className="session-time">{seen}</small>}
          </div>
        );
      })}
    </section>
  );
}

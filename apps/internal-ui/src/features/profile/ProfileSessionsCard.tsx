import { Icon } from "../../shared/icons";
import { Button } from "../../shared/ui-controls";

export function ProfileSessionsCard({ message, revoking, onRevoke }: { message: string; revoking: boolean; onRevoke: () => void }) {
  return (
    <section className="sessions-card">
      <div className="sessions-head"><h3>Активные сессии</h3><Button className="sessions-revoke" type="button" variant="danger-outline" onClick={onRevoke} disabled={revoking}>{revoking ? "Завершение" : "Завершить другие сессии"}</Button></div>
      {message && <div className="profile-message sessions">{message}</div>}
      <div className="session-row"><span className="session-icon"><Icon name="user" /></span><span><strong>Браузер</strong><small>сейчас активна</small></span><b>текущая</b></div>
    </section>
  );
}

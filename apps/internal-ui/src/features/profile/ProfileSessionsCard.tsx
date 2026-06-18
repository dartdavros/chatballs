import { Icon } from "../../shared/icons";

export function ProfileSessionsCard({ message, revoking, onRevoke }: { message: string; revoking: boolean; onRevoke: () => void }) {
  return (
    <section className="sessions-card">
      <div className="sessions-head"><h3>Активные сессии</h3><button type="button" onClick={onRevoke} disabled={revoking}>{revoking ? "Завершение" : "Завершить другие сессии"}</button></div>
      {message && <div className="profile-message sessions">{message}</div>}
      <div className="session-row"><span className="session-icon"><Icon name="user" /></span><span><strong>Браузер</strong><small>сейчас активна</small></span><b>текущая</b></div>
    </section>
  );
}

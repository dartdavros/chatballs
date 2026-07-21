import type { SessionUser } from "../../types";
import { SwitchButton } from "../../shared/form-controls";

export function ProfileTotpCard({ user, message, saving, onToggle }: { user: SessionUser; message: string; saving: boolean; onToggle: () => void }) {
  return (
    <section className="profile-card totp-card">
      <div>
        <h3>Двухфакторная аутентификация (TOTP)</h3>
        <p>{user.totpEnabled ? "Включена. Для OWNER рекомендуется держать включённой." : "Отключена. Для роли OWNER настоятельно рекомендуется включить."}</p>
      </div>
      <SwitchButton checked={user.totpEnabled} className="ui-switch is-large" label="Переключить TOTP" onClick={onToggle} disabled={saving} />
      {message && <div className="security-note warning">{message}</div>}
      {user.totpEnabled && <div className="security-note ok">Приложение-аутентификатор подключено · последний код принят 5 мин назад</div>}
    </section>
  );
}

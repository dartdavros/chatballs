import type { SessionUser } from "../../types";
import { SwitchButton } from "../../shared/form-controls";
import { Icon } from "../../shared/icons";
import { lastSeenLabel } from "./model";

// «Двухфакторная аутентификация» (дизайн-базлайн v2, кадр P1): описание слева,
// переключатель справа, ниже — полоса состояния: зелёная при включённой 2FA,
// жёлтое предупреждение при выключенной (кадр P2).

export function ProfileTotpCard({ user, message, saving, onToggle }: { user: SessionUser; message: string; saving: boolean; onToggle: () => void }) {
  const enabled = user.totpEnabled;
  const lastUsed = lastSeenLabel(user.totpLastUsedAt);
  return (
    <section className="profile-card totp-card">
      <div className="totp-head">
        <div>
          <h3>Двухфакторная аутентификация</h3>
          <p>
            {enabled
              ? "Включена. Код из приложения-аутентификатора запрашивается при каждом входе."
              : "Отключена. Для владельца и администраторов настоятельно рекомендуется включить."}
          </p>
        </div>
        <SwitchButton checked={enabled} className="ui-switch is-large" label="Переключить двухфакторную аутентификацию" onClick={onToggle} disabled={saving} />
      </div>
      {message && <div className="profile-message">{message}</div>}
      <div className={`security-note ${enabled ? "ok" : "warning"}`}>
        <Icon name={enabled ? "check" : "warning"} size={15} strokeWidth={2.2} />
        <span>
          {enabled
            ? `Аутентификатор подключён${lastUsed ? ` · последний код принят ${lastUsed}` : ""}`
            : "Без второго фактора доступ к организации защищён только паролем"}
        </span>
      </div>
    </section>
  );
}

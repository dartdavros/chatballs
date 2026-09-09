import type { SessionUser } from "../../types";
import { SwitchButton } from "../../shared/form-controls";
import { Icon } from "../../shared/icons";
import { lastSeenLabel } from "./model";
import { t } from "../../i18n";

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
          <h3>{t("profile.two_factor_authentication")}</h3>
          <p>
            {enabled
              ? t("profile.code_from_authenticator_app_required")
              : t("profile.off_strongly_recommended_owner_administrators")}
          </p>
        </div>
        <SwitchButton checked={enabled} className="ui-switch is-large" label={t("profile.toggle_two_factor_authentication")} onClick={onToggle} disabled={saving} />
      </div>
      {message && <div className="profile-message">{message}</div>}
      <div className={`security-note ${enabled ? "ok" : "warning"}`}>
        <Icon name={enabled ? "check" : "warning"} size={15} strokeWidth={2.2} />
        <span>
          {enabled
            ? (lastUsed ? t("profile.authenticator_last_used", { date: lastUsed }) : t("profile.authenticator_connected"))
            : t("profile.without_second_factor_access_organization")}
        </span>
      </div>
    </section>
  );
}

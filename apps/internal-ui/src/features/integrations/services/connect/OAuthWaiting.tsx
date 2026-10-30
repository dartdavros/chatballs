import { t } from "../../../../i18n";
import { LogoSpinner } from "../../../../shared/icons";

/** Ожидание разрешения в окне сервиса. */
export function OAuthWaiting({ service, onReopen }: { service: string; onReopen: () => void }) {
  return (
    <div className="service-oauth-waiting">
      <LogoSpinner size={18} />
      <div>
        <strong>{t("services.oauth_waiting_title", { service })}</strong>
        <span>{t("services.oauth_waiting_text")}</span>
      </div>
      <button className="link" type="button" onClick={onReopen}>{t("services.oauth_reopen")}</button>
    </div>
  );
}

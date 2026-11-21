import { t } from "../../i18n";
import { SwitchButton } from "../../shared/form-controls";
import { LogoSpinner } from "../../shared/icons";
import type { useExternalChecks } from "./useExternalChecks";
import "./external-checks.css";

function safeLink(value: string): boolean {
  const authority = value.match(/^https?:\/\/([^/?#]+)/i)?.[1];
  if (!authority || authority.includes("@") || /[\s\\]/.test(value)) return false;
  try {
    return Boolean(new URL(value).hostname);
  } catch {
    return false;
  }
}

export function ExternalChecksPanel({ enabled, saving, saveFailed, failed, announcements, toggle }: ReturnType<typeof useExternalChecks>) {
  const label = t("updates.external_checks_label");
  const hint = t("updates.external_checks_hint");
  return (
    <>
      <section className="external-setting">
        <div className="settings-card-head">
          <div><strong>{label}</strong><small>{hint}</small></div>
          <SwitchButton checked={enabled} className="ui-switch" label={`${label} ${hint}`} disabled={saving} onClick={() => void toggle()} />
        </div>
        <div className="external-setting-status" aria-live="polite">
          {saving && <LogoSpinner size={20} />}
          {saveFailed && <p className="settings-section-error" role="alert">{t("updates.external_checks_save_error")}</p>}
        </div>
      </section>
      <section className="service-messages">
        <h3>{t("updates.announcements_title")}</h3>
        {!enabled && <p className="settings-card-note">{t("updates.announcements_disabled")}</p>}
        {failed && <p className="settings-section-error" role="alert">{t("updates.announcements_error")}</p>}
        {enabled && !failed && announcements === null && <p className="settings-card-note">{t("updates.announcements_waiting")}</p>}
        {announcements?.length === 0 && <p className="settings-card-note">{t("updates.announcements_empty")}</p>}
        {announcements?.map((message) => (
          <article className="service-message" key={message.id}>
            <h4>{message.title}</h4>
            <p className="settings-card-note">{message.text}</p>
            {safeLink(message.link) && <a className="link is-neutral" href={message.link} target="_blank" rel="noreferrer">{t("updates.announcement_details")}</a>}
          </article>
        ))}
      </section>
    </>
  );
}

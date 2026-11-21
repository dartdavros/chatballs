import { t } from "../../i18n";
import { SwitchButton } from "../../shared/form-controls";
import { LogoSpinner } from "../../shared/icons";
import "./external-checks.css";

export function ExternalChecksPanel({ enabled, saving, saveFailed, onToggle }: {
  enabled: boolean;
  saving: boolean;
  saveFailed: boolean;
  onToggle: () => void;
}) {
  const label = t("updates.external_checks_label");
  const hint = t("updates.external_checks_hint");
  return (
    <section className="external-setting">
      <div className="settings-card-head">
        <div><strong>{label}</strong><small>{hint}</small></div>
        <SwitchButton checked={enabled} className="ui-switch" label={`${label} ${hint}`} disabled={saving} onClick={onToggle} />
      </div>
      <div className="external-setting-status" aria-live="polite">
        {saving && <LogoSpinner size={20} />}
        {saveFailed && <p className="settings-section-error" role="alert">{t("updates.external_checks_save_error")}</p>}
      </div>
    </section>
  );
}

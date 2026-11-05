import { t } from "../../../i18n";
import { FormField, SwitchButton, TextAreaField } from "../../../shared/form-controls";
import { Button } from "../../../shared/ui-controls";
import type { Integration } from "../model";
import { ServerErrors } from "../external/ServerFormParts";
import { ServiceAlert } from "../services/connect/ServiceAlert";
import { EventSchema } from "./EventSchema";
import { ScenarioChoice } from "./ScenarioChoice";
import { useRuleEditor } from "./useRuleEditor";
import "../external/styles.css";
import "../site-fields/styles.css";
import "../services/services.css";
import "./styles.css";

export function SiteEventSection({ integration, onSaved }: { integration: Integration; onSaved: (next: Integration) => void }) {
  const editor = useRuleEditor(integration, onSaved);
  const { draft, change, busy, submitted } = editor;
  return <div className="portal-settings-inner server-content server-http-content">
    <div className="portal-settings-heading"><h3>{t("site_events.section")}</h3></div>
    {integration.config.siteEventAvailable === false && <ServiceAlert tone="error"
      title={t("site_events.unavailable_title")} text={t("site_events.unavailable_help")} />}
    <div className="portal-settings-card server-form">
      <div className="server-two-fields">
        <div><FormField label={t("site_events.name")} mono value={draft.name} disabled={busy}
          error={submitted && !draft.name.trim() ? t("site_events.required_field") : undefined}
          onChange={(name) => change({ ...draft, name })} /><small>{t("site_events.name_help")}</small></div>
        <ScenarioChoice status={editor.catalogStatus} items={editor.catalog} value={draft.scenario}
          onChange={(scenario) => change({ ...draft, scenario })} onRetry={editor.loadCatalog}
          invalid={submitted && !draft.scenario} disabled={busy} />
      </div>
      <div><TextAreaField label={t("site_events.invitation")} value={draft.invitation} disabled={busy}
        onChange={(invitation) => change({ ...draft, invitation })} /><small>{t("site_events.invitation_help")}</small></div>
      <div className="server-enabled"><span><strong>{t("site_events.active")}</strong><small>{t("site_events.active_help")}</small></span>
        <SwitchButton label={t("site_events.active")} className="ui-switch" checked={draft.active} disabled={busy} onClick={() => change({ ...draft, active: !draft.active })} /></div>
    </div>
    <EventSchema values={draft.schema} onChange={(schema) => change({ ...draft, schema })} disabled={busy} />
    <ServerErrors messages={editor.error ? [editor.error] : submitted && !editor.valid ? [t("site_events.invalid")] : []} />
    <div className="server-actions"><Button variant="primary" disabled={busy || editor.catalogStatus !== "ready"} onClick={() => void editor.save()}>
      {t(busy ? "common.saving" : "common.save")}</Button>
      <span className={`server-action-note${submitted && !editor.valid ? " is-invalid" : ""}`} role="status">
        {submitted && !editor.valid ? t("site_events.fix_errors") : editor.saved ? t("site_events.saved") : ""}
      </span></div>
  </div>;
}

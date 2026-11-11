import { t } from "../../../i18n";
import { pathFromRoute, routeFromPath } from "../../../router";
import { SelectField } from "../../../shared/form-controls";
import { LogoSpinner } from "../../../shared/icons";
import { ServerErrors } from "../external/ServerFormParts";
import type { Scenario } from "../scenarios/types";

export function ScenarioChoice({ status, items, value, onChange, onRetry, invalid, disabled }: {
  status: "loading" | "ready" | "error" | "empty"; items: Scenario[]; value: string;
  onChange: (value: string) => void; onRetry: () => void; invalid: boolean; disabled: boolean;
}) {
  const ready = status === "ready", loading = status === "loading", failed = status === "error";
  const href = pathFromRoute("scenarios", null, routeFromPath(location.pathname).organizationPublicId);
  return <div className="ev-catalog" data-catalog={status}>
    <SelectField label={t("site_events.scenario")} value={ready ? value : ""} onChange={onChange}
      options={[["", t(loading ? "site_events.catalog_loading" : "site_events.choose")],
        ...(ready ? items.map((row): [string, string] => [row.id, row.name]) : [])]}
      disabled={disabled || !ready} invalid={failed || invalid} adornment={loading ? <LogoSpinner size={16} /> : undefined} />
    <div className="ev-catalog-help" aria-live="polite">
      {failed ? <ServerErrors messages={[t("site_events.catalog_error")]} />
        : <small>{t(status === "empty" ? "site_events.catalog_empty" : "site_events.catalog_help")}</small>}
      <small>{failed ? <button type="button" className="link" onClick={onRetry}>{t("site_events.retry")}</button>
        : <a className="link" href={href} target="_blank" rel="noreferrer">{t("site_events.catalog")}</a>}</small>
    </div>
  </div>;
}

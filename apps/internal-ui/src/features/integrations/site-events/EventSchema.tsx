import { t } from "../../../i18n";
import { Button } from "../../../shared/ui-controls";
import { emptyField, type DraftField } from "./model";
import { SchemaRow } from "./SchemaRow";

export function EventSchema({ values, onChange, disabled }: { values: DraftField[]; onChange: (next: DraftField[]) => void; disabled: boolean }) {
  return <section className="site-fields-card ev-schema">
    <div className="site-fields-card-head"><strong>{t("site_events.schema")}</strong>
      <Button variant="primary" icon="plus" disabled={disabled || values.length >= 30} onClick={() => onChange([...values, emptyField()])}>{t("site_events.add_field")}</Button></div>
    <div className="ev-schema-scroll" tabIndex={0} role="region" aria-label={t("site_events.schema")}>
      <table className="site-fields-table ev-schema-table"><thead><tr>
        <th scope="col">{t("site_events.field")}</th><th scope="col">{t("site_events.type")}</th><th scope="col">{t("site_events.limits")}</th>
        <th scope="col">{t("site_events.required")}</th><th scope="col" className="ev-actions-heading">{t("site_events.actions")}</th>
      </tr></thead><tbody>{values.map((value, index) => <SchemaRow key={index} value={value} disabled={disabled}
        onChange={(next) => onChange(values.map((old, i) => i === index ? next : old))}
        onRemove={() => onChange(values.filter((_, i) => i !== index))} />)}</tbody></table>
    </div><div className="site-fields-footer">{t("site_events.schema_help")}</div>
  </section>;
}

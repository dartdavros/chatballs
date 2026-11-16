import { HelpTitle } from "./HelpTitle";
import { t } from "../../../i18n";
import { SwitchButton } from "../../../shared/form-controls";
import { StatusPill } from "../../../shared/ui";
import { et } from "./copy";
import { PolicyTarget } from "./PolicyTarget";
import type { ExternalBinding, SettingsCatalog, FieldRef } from "./model";

export const sameField = (first: FieldRef, second: FieldRef) => first.sourceConnectionId === second.sourceConnectionId && first.fieldId === second.fieldId;
const types = { string: "site_fields.string", number: "site_fields.number", boolean: "site_fields.boolean", datetime: "site_fields.datetime",
  enum: "site_fields.enum", email: "site_fields.email", phone: "site_fields.phone", url: "site_fields.url" } as const;
export type PolicyProps = {
  name: string; bindings: ExternalBinding[]; binding: ExternalBinding; catalog: SettingsCatalog;
  disabled: boolean; select: (id: number) => void; change: (patch: Partial<ExternalBinding>) => void;
};

export function DataPolicyCard({ name, bindings, binding, catalog, disabled, select, change }: PolicyProps) {
  const stale = (binding.staleGrants?.customFields ?? []).filter(ref => !catalog.customFields.some(field => sameField(field, ref)));
  const changed = (binding.staleGrants?.customFields ?? []).some(ref => catalog.customFields.some(field => sameField(field, ref)));
  function toggle(field: FieldRef) {
    const exists = binding.customFields.some(ref => sameField(ref, field));
    change({ customFields: exists ? binding.customFields.filter(ref => !sameField(ref, field))
      : [...binding.customFields, { sourceConnectionId: field.sourceConnectionId, fieldId: field.fieldId }] });
  }
  return <section className="administration-card" data-data-policy>
    <div className="settings-card-head"><div><HelpTitle title={et("policy.data")} topic="data" /><small>{et("policy.dataLead")}</small></div></div>
    <PolicyTarget name={name} bindings={bindings} agentId={binding.agentId} disabled={disabled} select={select} />
    <div className="service-connect-stack"><div className="site-fields-card"><div className="site-fields-card-head"><strong>{et("policy.standard")}</strong></div>
      <table className="site-fields-table"><thead><tr><th>{et("policy.field")}</th><th className="ui-switch-column">{et("policy.permission")}</th></tr></thead><tbody>
        {(["name", "email", "phone"] as const).map(field => <tr key={field}><td>{et(field === "name" ? "policy.contactName" : `policy.${field}`)}</td>
          <td className="ui-switch-cell"><SwitchButton className="ui-switch is-compact" checked={binding.standardFields.includes(field)} disabled={disabled}
            label={`${et("policy.permission")}: ${et(field === "name" ? "policy.contactName" : `policy.${field}`)}`}
            onClick={() => change({ standardFields: binding.standardFields.includes(field) ? binding.standardFields.filter(item => item !== field) : [...binding.standardFields, field] })} /></td></tr>)}
      </tbody></table>{!binding.standardFields.length && !stale.length && !changed && <div className="site-fields-footer">{et("policy.fieldsEmpty")}</div>}</div>
      <div className="site-fields-card"><div className="site-fields-card-head"><HelpTitle title={et("policy.custom")} topic="webFields" /></div>
        {!catalog.customFields.length && !stale.length ? <div className="site-fields-footer">{et("policy.sourcesEmpty")}</div>
          : <table className="site-fields-table"><thead><tr>{(["field", "source", "type", "permission"] as const).map(key => <th key={key}
            className={key === "permission" ? "ui-switch-column" : undefined}>{et(`policy.${key}`)}</th>)}</tr></thead><tbody>
            {catalog.customFields.map(field => <tr key={`${field.sourceConnectionId}:${field.fieldId}`}><td><span className="site-field-label">{field.label}</span>
              {binding.staleGrants?.customFields.some(ref => sameField(ref, field)) && <small className="site-field-access-note">{et("policy.fieldChanged")}</small>}</td>
              <td>{field.sourceName}</td><td><span className="site-field-type">{t(types[field.type as keyof typeof types] ?? "site_fields.string")}</span></td>
              <td className="ui-switch-cell">{binding.staleGrants?.customFields.some(ref => sameField(ref, field))
                ? <StatusPill status="pending" label={et("policy.noPermission")} />
                : <SwitchButton className="ui-switch is-compact" checked={binding.customFields.some(ref => sameField(ref, field))} disabled={disabled}
                  label={`${et("policy.permission")}: ${field.label} · ${field.sourceName}`} onClick={() => toggle(field)} />}</td></tr>)}
            {stale.map(ref => { const previous = binding.previousFields?.find(field => sameField(field, ref));
              const source = catalog.sources.find(item => item.id === ref.sourceConnectionId);
              return <tr key={`${ref.sourceConnectionId}:${ref.fieldId}`}><td><span className="site-field-label">{previous?.label ?? et("policy.fieldRemoved")}</span>
                <small className="site-field-access-note">{et(source ? "policy.fieldRemoved" : "policy.sourceRemoved")}</small></td>
              <td>{source?.name ?? previous?.sourceName ?? et("policy.sourceRemoved")}</td><td><span className="site-field-type">{previous && t(types[previous.type as keyof typeof types] ?? "site_fields.string")}</span></td>
              <td className="ui-switch-cell"><StatusPill status="pending" label={et("policy.noPermission")} /></td></tr>; })}
          </tbody></table>}
      </div></div>
    <p className="settings-section-note">{et("policy.notInherited")}</p>
    {(stale.length > 0 || changed) && <div className="administration-message error" role="alert">
      {stale.length > 0 && <p>{et("policy.removedLead")}</p>}{changed && <p>{et("policy.changedLead")}</p>}</div>}
  </section>;
}

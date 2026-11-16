import { HelpTitle } from "./HelpTitle";
import { SwitchButton } from "../../../shared/form-controls";
import { et } from "./copy";
import { PolicyTarget } from "./PolicyTarget";
import type { PolicyProps } from "./DataPolicyCard";
import { TemplateMessageLink } from "./TemplateMessageLink";

export function TemplatePolicyCard({ organization, name, bindings, binding, catalog, disabled, select, change }: PolicyProps & { organization: string }) {
  const stale = binding.staleGrants?.templateIds ?? [];
  return <section className="administration-card" data-template-grants>
    <div className="settings-card-head"><div><HelpTitle title={et("policy.templates")} topic="templates" /><small>{et("policy.templatesLead")}</small></div></div>
    <PolicyTarget name={name} bindings={bindings} agentId={binding.agentId} disabled={disabled} select={select} />
    {!binding.templateIds.length && !stale.length && <p className="settings-section-note">{et("policy.templatesEmpty")}</p>}
    {!catalog.templates.length && <p className="settings-section-note">{et("policy.templatesCatalogEmpty")}</p>}
    {catalog.templates.filter(template => !stale.includes(template.id)).map(template => <div className="service-preset" key={template.id}>
      <div><strong>{template.name}</strong><div><TemplateMessageLink organization={organization} id={template.id} title={template.name} /></div></div>
      <SwitchButton className="ui-switch is-compact" checked={binding.templateIds.includes(template.id)} disabled={disabled}
        label={`${et("policy.templatePermission")}: ${template.name}`} onClick={() => change({ templateIds: binding.templateIds.includes(template.id)
          ? binding.templateIds.filter(id => id !== template.id) : [...binding.templateIds, template.id] })} />
    </div>)}
    {stale.map(id => <div className="service-preset" key={id}><div><strong>{et("policy.templateUnavailable")}</strong><p>{et("policy.templatesStale")}</p></div>
      <SwitchButton className="ui-switch is-compact" checked={false} disabled label={et("policy.templatePermission")} onClick={() => undefined} /></div>)}
    <p className="settings-section-note">{et("policy.templateScope")}</p>
  </section>;
}

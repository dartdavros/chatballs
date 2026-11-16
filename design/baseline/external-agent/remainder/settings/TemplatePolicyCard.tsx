import { SwitchButton } from '../../../../../apps/internal-ui/src/shared/form-controls';
import { tx } from './copy';
import { PolicyTarget } from './PolicyTarget';
import { HelpTrigger } from '../shared/HelpTrigger';
import { TemplateMessageLink } from './TemplateMessageLink';

export function TemplatePolicyCard({ variant }: { variant: string }) {
  const selected = variant === 'S22', stale = variant === 'S23', empty = !selected && !stale;
  const noTemplates = variant === 'S21', disabled = ['S34', 'S38', 'S72'].includes(variant);
  return <section className="administration-card" data-template-grants={empty ? 'empty' : stale ? 'stale' : 'selected'}>
    <div className="settings-card-head"><div><span className="external-help-title"><strong>{tx('templates')}</strong><HelpTrigger topic="templates" /></span><small>{tx('templatesLead')}</small></div></div>
    <PolicyTarget disabled={disabled} />
    {empty && <p className="settings-section-note">{tx('templatesEmpty')}</p>}
    {noTemplates ? <p className="settings-section-note" data-template-catalog="empty">{tx('templatesCatalogEmpty')}</p>
      : (stale ? ['templateUnavailable'] as const : ['templateGreeting', 'templateOrder'] as const).map((key, index) => <div className="service-preset" key={key}>
        <div><strong>{tx(key)}</strong>{stale ? <p>{tx('templatesStale')}</p> : <div><TemplateMessageLink template={index === 0 ? 'greeting' : 'order'} /></div>}</div>
        <SwitchButton className="ui-switch is-compact" checked={selected && index === 0} disabled={stale || disabled}
          label={`${tx('templatePermission')}: ${tx(key)}`} onClick={() => {}} />
      </div>)}
    <p className="settings-section-note">{tx('templateScope')}</p>
  </section>;
}

import { SwitchButton } from '../../../../../apps/internal-ui/src/shared/form-controls';
import { StatusPill } from '../../../../../apps/internal-ui/src/shared/ui';
import { tx, type CopyKey } from './copy';
import { PolicyTarget } from './PolicyTarget';
import { HelpTrigger } from '../shared/HelpTrigger';

type FieldRow = { field: CopyKey; source: CopyKey; type: CopyKey; selected: boolean; issue?: CopyKey };
const selectedFields: FieldRow[] = [
  { field: 'city', source: 'sourceMain', type: 'textType', selected: true },
  { field: 'city', source: 'sourceShop', type: 'textType', selected: true },
  { field: 'tariff', source: 'sourceShop', type: 'enumType', selected: false },
];
const staleFields: FieldRow[] = [
  { field: 'city', source: 'sourceMain', type: 'textType', selected: false, issue: 'sourceRemoved' },
  { field: 'score', source: 'sourceShop', type: 'numberType', selected: false, issue: 'fieldRemoved' },
  { field: 'tariff', source: 'sourceShop', type: 'enumType', selected: false, issue: 'fieldChanged' },
];
function CustomFieldTable({ rows, disabled }: { rows: FieldRow[]; disabled: boolean }) {
  return <table className="site-fields-table"><thead><tr>
    {(['field', 'source', 'type', 'permission'] as const).map(key => <th key={key} className={key === 'permission' ? 'ui-switch-column' : undefined}>{tx(key)}</th>)}
  </tr></thead><tbody>{rows.map((row, index) => <tr key={`${row.source}-${index}`} data-custom-grant={row.issue ? 'stale' : row.selected ? 'selected' : 'off'}>
    <td><span className="site-field-label">{tx(row.field)}</span>{row.issue && <small className="site-field-access-note">{tx(row.issue)}</small>}</td>
    <td>{tx(row.source)}</td><td><span className="site-field-type">{tx(row.type)}</span></td>
    <td className="ui-switch-cell">{row.issue ? <StatusPill status="pending" label={tx('noPermission')} />
      : <SwitchButton className="ui-switch is-compact" checked={row.selected} disabled={disabled} label={`${tx('permission')}: ${tx(row.field)} · ${tx(row.source)}`} onClick={() => {}} />}</td>
  </tr>)}</tbody></table>;
}
export function DataPolicyCard({ variant }: { variant: string }) {
  const selected = variant === 'S22', stale = variant === 'S23', empty = !selected && !stale;
  const noSources = variant === 'S21', disabled = ['S34', 'S38', 'S72'].includes(variant);
  const rows = stale ? staleFields : selectedFields.map(field => ({ ...field, selected: selected && field.selected }));
  return <section className="administration-card" data-data-policy={empty ? 'empty' : stale ? 'stale' : 'selected'}>
    <div className="settings-card-head"><div><span className="external-help-title"><strong>{tx('data')}</strong><HelpTrigger topic="data" /></span><small>{tx('dataLead')}</small></div></div>
    <PolicyTarget disabled={disabled} />
    <div className="service-connect-stack">
      <div className="site-fields-card"><div className="site-fields-card-head"><strong>{tx('standard')}</strong></div>
        <table className="site-fields-table"><thead><tr><th>{tx('field')}</th><th className="ui-switch-column">{tx('permission')}</th></tr></thead>
          <tbody>{(['contactName', 'email', 'phone'] as const).map((field, index) => <tr key={field}>
            <td>{tx(field)}</td><td className="ui-switch-cell"><SwitchButton className="ui-switch is-compact" checked={selected && index < 2} disabled={disabled}
              label={`${tx('permission')}: ${tx(field)}`} onClick={() => {}} /></td>
          </tr>)}</tbody></table>
        {empty && <div className="site-fields-footer">{tx('fieldsEmpty')}</div>}
      </div>
      <div className="site-fields-card"><div className="site-fields-card-head"><span className="external-help-title"><strong>{tx('custom')}</strong><HelpTrigger topic="webFields" /></span></div>
        {noSources ? <div className="site-fields-footer">{tx('sourcesEmpty')}</div> : <CustomFieldTable rows={rows} disabled={disabled} />}
      </div>
    </div>
    <p className="settings-section-note">{tx('notInherited')}</p>
    {stale && <div className="administration-message error" role="alert"><p>{tx('removedLead')}</p><p>{tx('changedLead')}</p></div>}
  </section>;
}

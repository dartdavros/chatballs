import { SelectField, SwitchButton } from '../../../apps/internal-ui/src/shared/form-controls';
import { Button } from '../../../apps/internal-ui/src/shared/ui-controls';
import { tx } from './copy';

export function PermissionsCard() {
  return <section className="agent-card is-side">
    <h3>{tx('permissions')}</h3>
    <p>{tx('permissionsHelp')}</p>
    <div className="agent-side-fields">
      <SelectField label={tx('standard')} value="none" disabled onChange={() => {}} options={[["none", tx('noContact')]]} />
      <SelectField label={tx('custom')} value="none" disabled onChange={() => {}} options={[["none", tx('noCustom')]]} />
      <small className="settings-section-note">{tx('noneHelp')} {tx('fieldsLater')}</small>
      <SelectField label={tx('formats')} value="none" disabled onChange={() => {}} options={[["none", tx('noTemplates')]]} />
      <small className="settings-section-note">{tx('formatsHelp')} {tx('templateHelp')}</small>
      <div className="agent-assistance-toggle">
        <div><strong>{tx('initiative')}</strong><small>{tx('initiativeHelp')}</small></div>
        <SwitchButton label={tx('initiative')} checked={false} disabled className="ui-switch is-compact" onClick={() => {}} />
      </div>
      <small className="settings-section-note">{tx('sourceNote')}</small>
      <div className="agent-dirty"><small>{tx('savingDisabled')}</small>
        <Button variant="primary" disabled>{tx('save')}</Button></div>
    </div>
  </section>;
}

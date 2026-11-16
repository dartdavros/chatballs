import { FormField, SelectField } from '../../../apps/internal-ui/src/shared/form-controls';
import { Icon } from '../../../apps/internal-ui/src/shared/icons';
import { t } from '../../../apps/internal-ui/src/i18n';
import { LANGUAGES } from '../../../packages/shared/src';
import { tx } from './copy';

// Presentation of one state. Selection does not navigate to an unreviewed frame.
export function ExecutionCard() {
  return <section className="agent-card is-side">
    <h3>{tx('replies')}</h3>
    <p>{tx('executionHelp')}</p>
    <div className="agent-side-fields">
      <SelectField label={tx('execution')} value="external" onChange={() => {}}
        options={[["builtin", tx('builtin')], ["external", tx('external')]]} />
      <SelectField label={tx('connection')} value="" onChange={() => {}}
        options={[["", tx('chooseConnection')], ["service-example", tx('serviceExample')]]} />
      <small className="settings-section-note">{tx('connectionHelp')}</small>
      <FormField label={tx('externalId')} value="" disabled placeholder={tx('externalIdPlaceholder')} />
      <small className="settings-section-note">{tx('externalIdHelp')}</small>
      <div className="agent-feedback is-warning" role="status">
        <strong><Icon name="warning" size={15} /> {tx('setupTitle')}</strong>
        <div>{tx('setupHelp')}</div>
      </div>
      <div className="agent-field is-text agent-answer-language">
        <span>{t('ai.answer_language')}<small>{t('ai.answer_language_hint')}</small></span>
        <div className="appearance-theme-options">
          {[["MIRROR", t('ai.answer_language_mirror')], ["ORGANIZATION", t('ai.answer_language_organization')],
            ...LANGUAGES.map(item => [item.code, item.label])].map(([value, label]) =>
            <button type="button" className={value === 'MIRROR' ? 'active' : ''} key={value}>{label}</button>)}
        </div>
        <small className="settings-section-note">{tx('languageHelp')}</small>
      </div>
      <p className="settings-section-note">{tx('preserved')}</p>
    </div>
  </section>;
}

import { t } from '../../../../../apps/internal-ui/src/i18n';
import { Icon } from '../../../../../apps/internal-ui/src/shared/icons';
import { TestClientField } from '../../../../../apps/internal-ui/src/features/agents/test-chat/TestClientField';
import { noop } from './data';
import { tx } from './copy';
import { HelpTrigger } from '../shared/HelpTrigger';

export function TestClientFields() {
  return <section className="agent-test-data" data-permitted-fields="name,web-topic">
    <button type="button" className="agent-test-data-heading" aria-expanded="true">
      <Icon name="user" size={15} /><span><strong>{t('agent_test.client_data')}</strong></span>
      <span className="is-expanded"><Icon name="chevron" size={14} /></span></button>
    <div className="agent-test-fields"><small className="agent-test-data-hint">{tx('fieldsHelp')}</small>
      <TestClientField field={{key:'name',label:tx('name'),type:'string'}} id="test-name" value={tx('nameValue')} onChange={noop} disabled={false} />
      <span className="external-help-title"><strong className="agent-test-group">{tx('source')}</strong><HelpTrigger topic="webFields" /></span>
      <TestClientField field={{key:'topic',label:tx('topic'),type:'string'}} id="test-topic" value={tx('topicValue')} onChange={noop} disabled={false} />
    </div>
  </section>;
}

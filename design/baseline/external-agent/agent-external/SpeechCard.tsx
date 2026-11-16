import { t } from '../../../../apps/internal-ui/src/i18n';
import { FormField, SelectField } from '../../../../apps/internal-ui/src/shared/form-controls';
import { SynthesisSettings } from '../../../../apps/internal-ui/src/features/agents/SynthesisSettings';
import { agent, speechProviders, noop, unchanged } from './design-data';
import { tx } from './copy';

// Existing speech controls, with explicit STT instead of inheritance from the answer provider.
export function SpeechCard() {
  return <section className="agent-card agent-speech-settings" data-independent-stt>
    <div className="agent-card-head"><h3>{tx('speechTitle')}</h3></div>
    <p className="settings-section-note">{tx('speechHelp')}</p>
    <div className="agent-side-fields">
      <SelectField label={t('ai.transcription_provider')} value={String(agent.transcriptionIntegrationId)}
        onChange={noop} options={speechProviders.map(item => [String(item.id), item.name])} />
      <FormField label={t('ai.transcription_model')} mono value={agent.transcriptionModel}
        placeholder={agent.transcriptionProviderModel} onChange={noop} />
      <SelectField label={t('speech.language')} value={agent.transcriptionLanguage ?? ''} onChange={noop}
        options={[[ '', t('speech.organizationLanguage') ], [ 'ru-RU', t('portals.russian') ], [ 'en-US', t('portals.english') ]]} />
      <SynthesisSettings card={agent} providers={speechProviders} canManage busy={false} apply={unchanged} />
      <p className="settings-section-note">{t('speech.privacy')}</p>
    </div>
  </section>;
}

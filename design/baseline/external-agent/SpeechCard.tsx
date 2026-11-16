import { t } from '../../../apps/internal-ui/src/i18n';
import { FormField, SelectField } from '../../../apps/internal-ui/src/shared/form-controls';
import { SynthesisSettings } from '../../../apps/internal-ui/src/features/agents/SynthesisSettings';
import type { Integration } from '../../../apps/internal-ui/src/features/integrations/model';
import { card, speechProviders } from './design-data';
import { tx } from './copy';

// Same controls/order as SpeechSettings; STT cannot inherit the external reply service.
export function SpeechCard() {
  return <section className="agent-card is-side">
    <h3>{tx('speech')}</h3><p>{tx('speechHelp')}</p>
    <div className="agent-side-fields">
      <SelectField label={t('ai.transcription_provider')} value="3" options={[["3", 'SpeechKit']]} onChange={() => {}} />
      <FormField label={t('ai.transcription_model')} value="" placeholder="general" mono onChange={() => {}} />
      <SelectField label={t('speech.language')} value="" onChange={() => {}}
        options={[["", t('speech.organizationLanguage')], ["ru-RU", t('portals.russian')], ["en-US", t('portals.english')]]} />
      <SynthesisSettings card={card} providers={speechProviders as Integration[]} canManage busy={false} apply={async () => false} />
      <p className="settings-section-note">{t('speech.privacy')}</p>
    </div>
  </section>;
}

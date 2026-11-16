import { LANGUAGES } from '@chatballs/shared';
import { t } from '../../../../apps/internal-ui/src/i18n';
import { agent } from './design-data';
import { tx } from './copy';

export function ResponseLanguageCard() {
  const options = [
    { value: 'MIRROR', label: t('ai.answer_language_mirror'), lang: undefined },
    { value: 'ORGANIZATION', label: t('ai.answer_language_organization'), lang: undefined },
    ...LANGUAGES.map(item => ({ value: item.code, label: item.label, lang: item.code })),
  ];
  return <section className="agent-card">
    <div className="agent-card-head"><h3>{tx('responseTitle')}</h3></div>
    <div className="agent-field is-text agent-answer-language">
      <span>{t('ai.answer_language')}<small>{t('ai.answer_language_hint')}</small></span>
      <div className="appearance-theme-options">{options.map(option =>
        <button className={agent.answerLanguage === option.value ? 'active' : ''} key={option.value}
          lang={option.lang} type="button">{option.label}</button>)}</div>
    </div>
    <p className="settings-section-note">{tx('responseHelp')}</p>
  </section>;
}

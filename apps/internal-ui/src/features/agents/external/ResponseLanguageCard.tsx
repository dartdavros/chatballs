import { LANGUAGES } from "@chatballs/shared";
import { t } from "../../../i18n";
import { et } from "../../settings/external-agent/copy";
import type { AgentCard, AgentPatch } from "../model";

export function ResponseLanguageCard({ card, canManage, busy, apply }: {
  card: AgentCard; canManage: boolean; busy: boolean; apply: (patch: AgentPatch) => Promise<boolean>;
}) {
  const options = [{ value: "MIRROR", label: t("ai.answer_language_mirror"), lang: undefined },
    { value: "ORGANIZATION", label: t("ai.answer_language_organization"), lang: undefined },
    ...LANGUAGES.map(item => ({ value: item.code, label: item.label, lang: item.code }))];
  return <section className="agent-card"><div className="agent-card-head"><h3>{et("agentBase.responseTitle")}</h3></div>
    <div className="agent-field is-text agent-answer-language"><span>{t("ai.answer_language")}<small>{t("ai.answer_language_hint")}</small></span>
      {canManage ? <div className="appearance-theme-options">{options.map(option => <button key={option.value} type="button"
        className={card.answerLanguage === option.value ? "active" : ""} lang={option.lang} disabled={busy}
        onClick={() => void apply({ answerLanguage: option.value })}>{option.label}</button>)}</div>
        : <span className="agent-field-static">{options.find(option => option.value === card.answerLanguage)?.label ?? card.answerLanguage}</span>}
    </div><p className="settings-section-note">{et("agentBase.responseHelp")}</p>
  </section>;
}

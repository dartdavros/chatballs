import { useEffect, useState } from "react";
import { t } from "../../i18n";
import { FormField, SelectField } from "../../shared/form-controls";
import type { Integration } from "../integrations/model";
import type { AgentCard, AgentPatch } from "./model";
import { SynthesisSettings } from "./SynthesisSettings";

export function SpeechSettings({ card, providers, canManage, busy, apply }: {
  card: AgentCard; providers: Integration[]; canManage: boolean; busy: boolean;
  apply: (patch: AgentPatch) => Promise<boolean>;
}) {
  const [model, setModel] = useState(card.transcriptionModel);
  useEffect(() => setModel(card.transcriptionModel), [card.transcriptionModel]);
  const selected = providers.find((item) => item.id === (card.transcriptionIntegrationId ?? card.providerIntegrationId));
  const compatible = providers.filter((item) => item.speechCapabilities?.stt);
  const broken = card.transcriptionIntegrationId !== null && (!selected || !selected.isActive || selected.status === "ERROR" || !selected.speechCapabilities?.stt);
  const options: [string, string][] = compatible.map((item) => [String(item.id), item.name]);
  if (selected && !options.some(([id]) => id === String(selected.id))) options.push([String(selected.id), selected.name]);
  return <>
    <SelectField disabled={busy} label={t("ai.transcription_provider")} readOnly={!canManage}
      readOnlyText={selected?.name || t("ai.same_as_answers")} value={card.transcriptionIntegrationId ? String(card.transcriptionIntegrationId) : ""}
      onChange={(value) => void apply({ transcriptionIntegrationId: value ? Number(value) : null, transcriptionModel: "" })}
      options={[["", t("ai.same_as_answers")], ...options]} />
    {!card.transcriptionIntegrationId && <small className="settings-section-note">{t("speech.inheritHelp")}</small>}
    <FormField disabled={busy || !canManage} label={t("ai.transcription_model")} mono
      placeholder={card.transcriptionProviderModel || selected?.speechCapabilities?.default_model || t("ai.model_of_integration")}
      value={model} onChange={setModel} onBlur={() => { if (model !== card.transcriptionModel) void apply({ transcriptionModel: model }); }} />
    <SelectField disabled={busy || !canManage} label={t("speech.language")} value={card.transcriptionLanguage ?? ""}
      onChange={(value) => void apply({ transcriptionLanguage: value })}
      options={[["", t("speech.organizationLanguage")], ["ru-RU", t("portals.russian")], ["en-US", t("portals.english")]]} />
    {broken && <div className="integration-form-error" role="alert">{t("speech.explicitError")}</div>}
    <SynthesisSettings card={card} providers={providers} canManage={canManage} busy={busy} apply={apply} />
    <p className="settings-section-note">{t("speech.privacy")}</p>
  </>;
}

import { useEffect, useState } from "react";
import { t } from "../../i18n";
import { FormField, SelectField } from "../../shared/form-controls";
import type { Integration } from "../integrations/model";
import type { AgentCard, AgentPatch } from "./model";

export function SynthesisSettings({ card, providers, canManage, busy, apply }: {
  card: AgentCard; providers: Integration[]; canManage: boolean; busy: boolean;
  apply: (patch: AgentPatch) => Promise<boolean>;
}) {
  const [model, setModel] = useState(card.synthesisModel ?? "");
  useEffect(() => setModel(card.synthesisModel ?? ""), [card.synthesisModel]);
  const selected = providers.find(item => item.id === card.synthesisIntegrationId);
  const compatible = providers.filter(item => item.speechCapabilities?.tts);
  const options: [string, string][] = compatible.map(item => [String(item.id), item.name]);
  if (selected && !options.some(([id]) => id === String(selected.id))) options.push([String(selected.id), selected.name]);
  const languageNames: Record<string, string> = { "ru-RU": t("portals.russian"), "en-US": t("portals.english") };
  const voices: [string, string][] = selected?.speechCapabilities?.voices?.map(voice =>
    [voice.id, [voice.id, languageNames[voice.language]].filter(Boolean).join(" · ")]) ?? [];
  if (card.synthesisVoice && !voices.some(([id]) => id === card.synthesisVoice)) voices.push([card.synthesisVoice, card.synthesisVoice]);
  const broken = card.synthesisIntegrationId && (!selected || !selected.isActive || !selected.speechCapabilities?.tts);
  return <>
    <SelectField label={t("speech.ttsProvider")} disabled={busy} readOnly={!canManage}
      readOnlyText={selected?.name || t("speech.disabled")} value={card.synthesisIntegrationId ? String(card.synthesisIntegrationId) : ""}
      onChange={value => void apply({ synthesisIntegrationId: value ? Number(value) : null, synthesisModel: "", synthesisVoice: "" })}
      options={[["", t("speech.disabled")], ...options]} />
    <FormField label={t("speech.ttsModel")} disabled={busy || !canManage || !selected} mono
      value={model} onChange={setModel} placeholder={t("speech.modelDefault")}
      onBlur={() => { if (model !== (card.synthesisModel ?? "")) void apply({ synthesisModel: model }); }} />
    <SelectField label={t("speech.voice")} value={card.synthesisVoice ?? ""} disabled={busy || !canManage || !selected}
      onChange={value => void apply({ synthesisVoice: value })} options={[["", t("speech.disabled")], ...voices]} />
    <small className="settings-section-note">{t("speech.voiceHelp")}</small>
    {broken && <div className="integration-form-error" role="alert">{t("speech.explicitError")}</div>}
  </>;
}

import type { MicrophoneMode } from "@chatballs/contracts";
import { t } from "../../../i18n";
import { FormField, SelectField, SwitchButton } from "../../../shared/form-controls";
import "../external/styles.css";

export type WebRecordingDraft = { microphoneMode: MicrophoneMode; maxSize: string; maxSeconds: string; answerPlaybackEnabled?: boolean };
export const validRecording = (draft: WebRecordingDraft) =>
  Number(draft.maxSize) > 0 && Number.isInteger(Number(draft.maxSize) * 1048576) && Number(draft.maxSize) <= 10
  && /^\d+$/.test(draft.maxSeconds) && Number(draft.maxSeconds) > 0 && Number(draft.maxSeconds) <= 60;

export function WebRecordingFields({ value, onChange, hasAgent }: { value: WebRecordingDraft; onChange: (next: WebRecordingDraft) => void; hasAgent: boolean }) {
  const valid = validRecording(value);
  return <>
    <div><SelectField label={t("speech.microphone")} value={value.microphoneMode}
      onChange={(mode) => onChange({ ...value, microphoneMode: mode as MicrophoneMode })}
      options={[["off", t("speech.off")], ["voice_message", t("speech.voiceMode")], ...(hasAgent || value.microphoneMode === "dictation" ? [["dictation", t("speech.dictationMode")] as [string, string]] : [])]} />
      <div className="integration-form-hint">{t("speech.modeHelp")}</div>
    </div>
    <div className="server-two-fields">
      <div><FormField label={t("speech.maxSize")} type="number" value={value.maxSize} onChange={(maxSize) => onChange({ ...value, maxSize })} error={valid ? undefined : t("speech.limitsError")} />
        <div className="integration-form-hint">{t("speech.sizeHelp")}</div></div>
      <div><FormField label={t("speech.maxDuration")} type="number" value={value.maxSeconds} onChange={(maxSeconds) => onChange({ ...value, maxSeconds })} disabled={value.microphoneMode !== "dictation"} />
        <div className="integration-form-hint">{t("speech.durationHelp")}</div></div>
    </div>
    <div className="server-enabled"><span><strong>{t("speech.listenWeb")}</strong><small>{t("speech.listenHelp")}</small></span><SwitchButton className="ui-switch" label={t("speech.listenWeb")} checked={Boolean(value.answerPlaybackEnabled)} disabled={!hasAgent}
      onClick={() => onChange({ ...value, answerPlaybackEnabled: !value.answerPlaybackEnabled })} /></div>
    <p className="settings-section-note">{t(hasAgent ? "speech.defaultsHelp" : "speech.noAgent")}</p>
    <p className="settings-section-note">{t("speech.privacy")}</p>
  </>;
}

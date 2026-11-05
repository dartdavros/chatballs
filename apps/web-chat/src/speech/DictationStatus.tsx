import { Loader } from "@chatballs/ui";
import { t, tn } from "../i18n";
import { formatBytes } from "../chatFormat";
import { SpeechIcon } from "./SpeechIcon";
import type { useDictation } from "./useDictation";

export type ComposerDictation = ReturnType<typeof useDictation>;
const seconds = (value: number) => `${Math.floor(value / 60)}:${String(value % 60).padStart(2, "0")}`;

export function DictationStatus({ dictation, tooLong }: { dictation: ComposerDictation; tooLong: boolean }) {
  if (!dictation.notice) return null;
  const notice = tooLong && !dictation.busy ? "tooLong" : dictation.notice;
  const loading = notice === "recognizing" || notice === "permission";
  const error = ["tooLong", "emptySpeech", "unsupported", "denied", "limitError", "formatError", "networkError", "providerError", "timeoutError"].includes(notice);
  const label = notice === "recognizing" && dictation.limit
    ? dictation.limit === "duration"
      ? tn("speech.durationLimit", dictation.maxSeconds)
      : t("speech.sizeLimit", { size: formatBytes(dictation.maxBytes) })
    : t(`speech.${notice}`);
  return <div className={`wc-dictation-status ${error ? "is-error" : ""}`} role="status" aria-live="polite">
    <div className="wc-dictation-copy"><div className="wc-dictation-heading">
      {loading && <Loader size={20} />}
      {dictation.recording && <strong className="wc-dictation-timer">{seconds(dictation.seconds)} / {seconds(dictation.maxSeconds)}</strong>}
      <span>{label}</span>
    </div></div>
    <div className="wc-dictation-actions">
      {dictation.retryable && <button className="wc-icon-button cb-composer-button" onClick={dictation.retry} aria-label={t("speech.retry")}><SpeechIcon name="refresh" /></button>}
      {error && !dictation.retryable && <button className="wc-icon-button cb-composer-button" onClick={dictation.start} aria-label={t("speech.recordAgain")}><SpeechIcon name="mic" /></button>}
      {dictation.recording && <button className="wc-icon-button cb-composer-button wc-dictation-stop" onClick={dictation.stop} aria-label={t("speech.stop")}><SpeechIcon name="stop" size={20} /></button>}
      <button className="wc-icon-button cb-composer-button" onClick={dictation.cancel} aria-label={t("speech.cancel")}><SpeechIcon name="close" /></button>
    </div>
  </div>;
}

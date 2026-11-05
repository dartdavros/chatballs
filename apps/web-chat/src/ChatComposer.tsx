import { useEffect, useRef } from "react";
import type { useVoiceRecorder } from "./useVoiceRecorder";
import { formatBytes } from "./chatFormat";
import { t } from "./i18n";
import { widgetClasses as classes } from "./widgetClasses";
import { DictationStatus, type ComposerDictation } from "./speech/DictationStatus";
import { SpeechIcon } from "./speech/SpeechIcon";

export type ComposerVoice = ReturnType<typeof useVoiceRecorder>;
function formatSeconds(total: number): string {
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

const COMPOSER_MAX_HEIGHT = 132;

export type ComposerAttachment = { file: File | null; errorText: string; pick: (file: File | null) => void; clear: () => void };

export function ChatComposer({ accent, input, placeholder, onInput, onSend, voice, attachment, dictation }: { accent: string; input: string; placeholder?: string; onInput: (value: string) => void; onSend: () => void; voice?: ComposerVoice; attachment?: ComposerAttachment; dictation?: ComposerDictation }) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  // Пока клиент не начал печатать, справа — запись голосового; как только в
  // поле появился текст, её место занимает отправка.
  const typing = Boolean(input.trim()) || Boolean(attachment?.file);

  // Поле растёт под текст, как в мессенджере (до COMPOSER_MAX_HEIGHT, дальше скролл).
  useEffect(() => {
    const node = textareaRef.current;
    if (!node) return;
    node.style.height = "auto";
    // Мерить можно только разложенное поле. У скрытой панели (display:none у
    // iframe) scrollHeight равен нулю, а у ещё не разложенной ширина нулевая и
    // placeholder переносится по букве — тогда замер даёт максимум, и поле
    // остаётся растянутым на всю высоту. В обоих случаях высоту не трогаем:
    // пустое поле и так в одну строку.
    if (!input || node.clientWidth === 0 || node.scrollHeight === 0) {
      node.style.height = "";
      return;
    }
    node.style.height = `${Math.min(node.scrollHeight, COMPOSER_MAX_HEIGHT)}px`;
  }, [input]);

  if (voice && voice.state !== "idle") {
    // Режим записи (кадр H, упрощённый для виджета): корзина · таймер · отправить.
    const sending = voice.state === "sending";
    return (
      <div className={classes.composer} style={{ "--cb-accent": accent } as React.CSSProperties}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, minHeight: 44, boxSizing: "border-box" }}>
          <button className={`wc-icon-button ${classes.composerButton}`} onClick={voice.cancel} disabled={sending} aria-label={t("chat.cancel_recording")}><svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" /><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></svg></button>
          <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#f5222d", flex: "none", animation: "wcTyping 1.2s infinite ease-in-out" }} />
          <span style={{ fontSize: 13.5, fontWeight: 600, color: "#f5222d", fontVariantNumeric: "tabular-nums" }}>{formatSeconds(voice.seconds)}</span>
          <span style={{ flex: 1, fontSize: 12.5, color: "#8c8c8c" }}>{sending ? t("chat.sending") : voice.state === "permission" ? t("speech.permission") : t("chat.recording")}</span>
          <button className={`wc-icon-button ${classes.composerButton} ${classes.sendButton}`} onClick={voice.stopAndSend} disabled={sending} aria-label={t("chat.send_voice")}><svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="19" x2="12" y2="5" /><polyline points="5 12 12 5 19 12" /></svg></button>
        </div>
      </div>
    );
  }

  return (
    <div className={classes.composer} style={{ "--cb-accent": accent } as React.CSSProperties}>
      {dictation && <DictationStatus dictation={dictation} tooLong={input.trim().length > 4000} />}
      {voice?.errorText && <div style={{ marginBottom: 8, fontSize: 12, color: "#cf1322" }}>{voice.errorText}</div>}
      {attachment?.errorText && <div style={{ marginBottom: 8, fontSize: 12, color: "#cf1322" }}>{attachment.errorText}</div>}
      {attachment?.file && (
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, padding: "6px 8px 6px 10px", border: "1px solid #e8e8e8", borderRadius: 10, background: "#fafafa", fontSize: 12.5, color: "#434343" }}>
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="#8c8c8c" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48" /></svg>
          <span style={{ flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontWeight: 600 }}>{attachment.file.name}</span>
          <span style={{ color: "#8c8c8c", fontSize: 11.5, flex: "none" }}>{formatBytes(attachment.file.size)}</span>
          <button onClick={attachment.clear} aria-label={t("chat.remove_file")} style={{ border: "none", background: "transparent", padding: 0, display: "flex", cursor: "pointer", color: "#8c8c8c", flex: "none" }}><svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><path d="m15 9-6 6M9 9l6 6" /></svg></button>
        </div>
      )}
      <div style={{ display: "flex", alignItems: "flex-start", gap: 4 }}>
        {attachment && (
          <>
            <button className={`wc-icon-button ${classes.composerButton}`} onClick={() => fileInputRef.current?.click()} aria-label={t("chat.attach_file")}><svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48" /></svg></button>
            <input ref={fileInputRef} type="file" hidden onChange={(event) => { attachment.pick(event.target.files?.[0] ?? null); event.target.value = ""; }} />
          </>
        )}
        <textarea ref={textareaRef} rows={1} value={input} onChange={(event) => onInput(event.target.value)} onKeyDown={(event) => { if (event.key === "Escape") dictation?.cancel(); if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); if (!dictation?.busy && input.trim().length <= 4000) onSend(); } }} placeholder={placeholder ?? t("chat.message_placeholder")} className={classes.composerInput} />
        {dictation && <button className={`wc-icon-button ${classes.composerButton} ${classes.recordButton} wc-dictation-trigger`} onClick={dictation.start} disabled={!dictation.available || dictation.busy || dictation.notice === "unsupported"} aria-label={t("speech.dictate")}><SpeechIcon name="mic" /></button>}
        {voice?.supported && !typing
          ? <button className={`wc-icon-button ${classes.composerButton} ${classes.recordButton}`} onClick={() => void voice.start()} aria-label={t("chat.record_voice")}><svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" /><path d="M19 10v2a7 7 0 0 1-14 0v-2" /><line x1="12" y1="19" x2="12" y2="22" /></svg></button>
          : <button className={`wc-icon-button ${classes.composerButton} ${classes.sendButton}`} onClick={onSend} disabled={Boolean(dictation?.busy) || input.trim().length > 4000 || (!typing && Boolean(dictation))} aria-label={t("chat.send")}><svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="19" x2="12" y2="5" /><polyline points="5 12 12 5 19 12" /></svg></button>}
      </div>
    </div>
  );
}


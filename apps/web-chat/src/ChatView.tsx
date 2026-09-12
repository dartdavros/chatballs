import { useEffect, useRef, useState, type RefObject } from "react";

import { isVideoCall, type CallInfo, type WebConfig, type WebMessage } from "./api";
import type { useVoiceRecorder } from "./useVoiceRecorder";
import { fmt, t } from "./i18n";

export type ComposerVoice = ReturnType<typeof useVoiceRecorder>;

function formatSeconds(total: number): string {
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

export function ChatHeader({ accent, letter, title, statusLabel, statusDot, unavailable, onClose }: { accent: string; letter: string; title: string; statusLabel: string; statusDot: string; unavailable: boolean; onClose: () => void }) {
  return (
    <div style={{ flex: "none", background: accent, padding: "14px 16px", display: "flex", alignItems: "center", gap: 11 }}>
      <div style={{ width: 36, height: 36, borderRadius: 10, background: "rgba(255,255,255,0.18)", display: "flex", alignItems: "center", justifyContent: "center", flex: "none", fontSize: 15, fontWeight: 700, color: "#fff" }}>{letter}</div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 14.5, fontWeight: 600, color: "#fff", lineHeight: 1.2 }}>{title}</div>
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 2 }}>
          <span style={{ width: 7, height: 7, borderRadius: "50%", background: statusDot, flex: "none" }} />
          <span style={{ fontSize: 11.5, color: "rgba(255,255,255,0.92)" }}>{unavailable ? t("chat.temporarily_unavailable") : statusLabel}</span>
        </div>
      </div>
      <button onClick={onClose} aria-label={t("chat.collapse")} style={{ width: 30, height: 30, borderRadius: 8, border: "none", background: "rgba(255,255,255,0.14)", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", flex: "none" }}>
        <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><line x1="5" y1="12" x2="19" y2="12" /></svg>
      </button>
    </div>
  );
}

export function ChatBody({ bodyRef, config, unavailable, accepted, accent, letter, title, messages, pending, awaiting, lastContactRequestId, showPhoneForm, onSubmitContact, audioUrlFor, attachmentUrlFor }: {
  bodyRef: RefObject<HTMLDivElement | null>;
  config: WebConfig | null;
  unavailable: boolean;
  accepted: boolean;
  accent: string;
  letter: string;
  title: string;
  messages: WebMessage[];
  pending: string[];
  awaiting: boolean;
  lastContactRequestId: number;
  showPhoneForm: boolean;
  onSubmitContact: (phone: string) => Promise<boolean>;
  audioUrlFor?: (messageId: number) => string;
  attachmentUrlFor?: (messageId: number, inline: boolean) => string;
}) {
  return (
    <div ref={bodyRef} style={{ flex: 1, minHeight: 0, overflowY: "auto", background: "#f7f8fa", padding: "18px 16px" }}>
      {config === null && <div style={{ textAlign: "center", color: "#8c8c8c", padding: 24, fontSize: 13 }}>{t("chat.loading")}</div>}
      {unavailable && <Unavailable />}
      {config?.available && !accepted && <Consent config={config} accent={accent} letter={letter} title={title} />}
      {config?.available && accepted && (
        <>
          <div style={{ textAlign: "center", marginBottom: 14 }}><span style={{ display: "inline-block", padding: "3px 11px", borderRadius: 20, background: "#eef0f2", fontSize: 11, color: "#8c8c8c" }}>{t("chat.today")}</span></div>
          {config.greeting && <Bubble author="ai" text={config.greeting} accent={accent} />}
          {messages.map((message) => message.author === "system"
            ? <SystemMessage key={message.id} text={message.text} />
            : <div key={message.id}><Bubble author={message.author} text={message.hasAudio ? "" : message.text || (message.kind === "voice" ? t("chat.voice_message") : "")} accent={accent} time={message.createdAt} audioUrl={message.hasAudio && audioUrlFor ? audioUrlFor(message.id) : undefined} attachment={message.kind === "file" && message.attachment ? { ...message.attachment, url: message.attachment.available && attachmentUrlFor ? attachmentUrlFor(message.id, false) : "", inlineUrl: message.attachment.available && attachmentUrlFor ? attachmentUrlFor(message.id, true) : "" } : undefined} />{message.kind === "contact_request" && message.id === lastContactRequestId && showPhoneForm && <PhoneForm accent={accent} onSubmit={onSubmitContact} />}</div>)}
          {pending.map((text, index) => <Bubble key={`p${index}`} author="client" text={text} accent={accent} pendingState />)}
          {awaiting && <Typing />}
        </>
      )}
    </div>
  );
}

function Unavailable() {
  return <div style={{ display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center", padding: "26px 14px" }}><div style={{ width: 52, height: 52, borderRadius: "50%", background: "#fff7e6", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 14 }}><svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="#d48806" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg></div><h3 style={{ margin: 0, fontSize: 15, fontWeight: 700 }}>{t("chat.unavailable_title")}</h3><p style={{ margin: "8px 0 0", fontSize: 13, color: "#595959", lineHeight: 1.5, maxWidth: 280 }}>{t("chat.unavailable_body")}</p></div>;
}

function Consent({ config, accent, letter, title }: { config: WebConfig; accent: string; letter: string; title: string }) {
  return <><div style={{ display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center", padding: "20px 12px 8px" }}><div style={{ width: 56, height: 56, borderRadius: 16, background: "#e6f4ff", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 14 }}><span style={{ fontSize: 24, fontWeight: 700, color: accent }}>{letter}</span></div><h3 style={{ margin: 0, fontSize: 17, fontWeight: 700 }}>{title}</h3><p style={{ margin: "8px 0 0", fontSize: 13, color: "#595959", lineHeight: 1.5, maxWidth: 280 }}>{config.greeting}</p></div><div style={{ marginTop: 18, background: "#fff", border: "1px solid #f0f0f0", borderRadius: 12, padding: 14 }}><div style={{ fontSize: 12, color: "#595959", lineHeight: 1.5 }}>{config.consent?.text} · {t("chat.consent_revision", { version: config.consent?.version ?? "" })}</div></div></>;
}

export function SystemMessage({ text }: { text: string }) {
  return <div style={{ textAlign: "center", margin: "12px 0" }}><span style={{ display: "inline-block", padding: "4px 12px", borderRadius: 20, background: "#e6f4ff", border: "1px solid #91caff", fontSize: 11.5, color: "#0958d9" }}>{text}</span></div>;
}

export function StartChatFooter({ accent, starting, onAccept }: { accent: string; starting: boolean; onAccept: () => void }) {
  return <div style={{ flex: "none", background: "#fff", borderTop: "1px solid #f0f0f0", padding: "12px 14px 14px" }}><button onClick={onAccept} disabled={starting} style={{ width: "100%", height: 44, borderRadius: 10, border: "none", background: accent, color: "#fff", fontSize: 14, fontWeight: 600, cursor: "pointer" }}>{starting ? t("chat.starting") : t("chat.accept_and_start")}</button></div>;
}

const COMPOSER_MAX_HEIGHT = 132;

export type ComposerAttachment = { file: File | null; errorText: string; pick: (file: File | null) => void; clear: () => void };

export function ChatComposer({ accent, state, quickReplies, pendingCount, messageCount, input, placeholder, onInput, onSend, voice, attachment }: { accent: string; state: "ai" | "operator" | "waiting"; quickReplies: string[]; pendingCount: number; messageCount: number; input: string; placeholder?: string; onInput: (value: string) => void; onSend: () => void; voice?: ComposerVoice; attachment?: ComposerAttachment }) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Поле растёт под текст, как в мессенджере (до COMPOSER_MAX_HEIGHT, дальше скролл).
  useEffect(() => {
    const node = textareaRef.current;
    if (!node) return;
    node.style.height = "auto";
    // Панель может быть ещё скрыта (у iframe display:none) — тогда scrollHeight
    // равен нулю и высоту задавать нельзя, иначе поле схлопнется.
    node.style.height = node.scrollHeight > 0 ? `${Math.min(node.scrollHeight, COMPOSER_MAX_HEIGHT)}px` : "";
  }, [input]);

  if (voice && voice.state !== "idle") {
    // Режим записи (кадр H, упрощённый для виджета): корзина · таймер · отправить.
    const sending = voice.state === "sending";
    return (
      <div style={{ flex: "none", background: "#fff", borderTop: "1px solid #f0f0f0", padding: "12px 14px 14px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, border: "1px solid #e8e8e8", borderRadius: 14, padding: "6px 6px 6px 10px", minHeight: 48, boxSizing: "border-box" }}>
          <button onClick={voice.cancel} disabled={sending} aria-label={t("chat.cancel_recording")} style={{ width: 34, height: 34, borderRadius: 9, border: "none", background: "transparent", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", flex: "none" }}><svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="#8c8c8c" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" /><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></svg></button>
          <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#f5222d", flex: "none", animation: "wcTyping 1.2s infinite ease-in-out" }} />
          <span style={{ fontSize: 13.5, fontWeight: 600, color: "#f5222d", fontVariantNumeric: "tabular-nums" }}>{formatSeconds(voice.seconds)}</span>
          <span style={{ flex: 1, fontSize: 12.5, color: "#8c8c8c" }}>{sending ? t("chat.sending") : t("chat.recording")}</span>
          <button onClick={voice.stopAndSend} disabled={sending} aria-label={t("chat.send_voice")} style={{ width: 36, height: 36, borderRadius: 10, border: "none", background: accent, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", flex: "none", opacity: sending ? 0.6 : 1 }}><svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></svg></button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ flex: "none", background: "#fff", borderTop: "1px solid #f0f0f0", padding: "12px 14px 14px" }}>
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
      {state === "ai" && quickReplies.length > 0 && pendingCount === 0 && messageCount === 0 && <div style={{ display: "flex", gap: 7, flexWrap: "wrap", marginBottom: 10 }}>{quickReplies.map((reply) => <button key={reply} onClick={() => onInput(reply)} style={{ padding: "7px 13px", borderRadius: 16, border: "1px solid #d6e4ff", background: "#f0f7ff", color: "#0958d9", fontSize: 12.5, fontWeight: 500, cursor: "pointer" }}>{reply}</button>)}</div>}
      <div style={{ display: "flex", alignItems: "flex-end", gap: 8, border: "1px solid #e8e8e8", borderRadius: 14, padding: "6px 6px 6px 14px", background: "#fff" }}>
        <textarea ref={textareaRef} rows={1} value={input} onChange={(event) => onInput(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); onSend(); } }} placeholder={placeholder ?? t("chat.message_placeholder")} style={{ flex: 1, border: "none", outline: "none", resize: "none", fontSize: 14, lineHeight: 1.5, color: "#262626", fontFamily: "inherit", padding: "7px 0", maxHeight: COMPOSER_MAX_HEIGHT }} />
        {attachment && (
          <>
            <button onClick={() => fileInputRef.current?.click()} aria-label={t("chat.attach_file")} style={{ width: 36, height: 36, borderRadius: 10, border: "none", background: "transparent", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", flex: "none" }}><svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="#8c8c8c" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48" /></svg></button>
            <input ref={fileInputRef} type="file" hidden onChange={(event) => { attachment.pick(event.target.files?.[0] ?? null); event.target.value = ""; }} />
          </>
        )}
        {voice?.supported && !input.trim() && !attachment?.file && (
          <button onClick={() => void voice.start()} aria-label={t("chat.record_voice")} style={{ width: 36, height: 36, borderRadius: 10, border: "none", background: "transparent", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", flex: "none" }}><svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="#8c8c8c" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" /><path d="M19 10v2a7 7 0 0 1-14 0v-2" /><line x1="12" y1="19" x2="12" y2="22" /></svg></button>
        )}
        <button onClick={onSend} aria-label={t("chat.send")} style={{ width: 36, height: 36, borderRadius: 10, border: "none", background: accent, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", flex: "none" }}><svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></svg></button>
      </div>
    </div>
  );
}

export function CallInviteBanner({ call, accent, onAccept, onDecline }: { call: CallInfo; accent: string; onAccept: () => void; onDecline: () => void }) {
  const phoneIcon = (rotated: boolean) => <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#fff" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" style={rotated ? { transform: "rotate(135deg)" } : undefined}><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.81.36 1.6.7 2.34a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.74-1.27a2 2 0 0 1 2.11-.45c.74.34 1.53.57 2.34.7A2 2 0 0 1 22 16.92z" /></svg>;
  const isVideo = isVideoCall(call);
  const inviteIcon = isVideo
    ? <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#fff" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M23 7l-7 5 7 5V7z" /><rect x="1" y="5" width="15" height="14" rx="2.5" /></svg>
    : <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#fff" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.81.36 1.6.7 2.34a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.74-1.27a2 2 0 0 1 2.11-.45c.74.34 1.53.57 2.34.7A2 2 0 0 1 22 16.92z" /></svg>;
  const title = isVideo ? t("chat.incoming_video_call") : t("chat.incoming_audio_call");
  return <div style={{ flex: "none", background: "#fff", borderTop: "1px solid #f0f0f0", padding: "12px 14px", display: "flex", alignItems: "center", gap: 12 }}><div style={{ width: 40, height: 40, borderRadius: "50%", background: accent, display: "flex", alignItems: "center", justifyContent: "center", flex: "none" }}>{inviteIcon}</div><div style={{ flex: 1, minWidth: 0 }}><div style={{ fontSize: 13.5, fontWeight: 600, color: "#1f1f1f" }}>{title}</div><div style={{ fontSize: 12, color: "#8c8c8c", marginTop: 2, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{t("chat.invites_you_to_call", { name: call.staffName || t("call.operator") })}</div></div><button onClick={onDecline} aria-label={t("call.decline")} style={{ width: 42, height: 42, borderRadius: "50%", border: "none", background: "#ff4d4f", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", flex: "none", boxShadow: "0 2px 8px rgba(255,77,79,.35)" }}>{phoneIcon(true)}</button><button onClick={onAccept} aria-label={t("call.accept")} style={{ width: 42, height: 42, borderRadius: "50%", border: "none", background: "#52c41a", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", flex: "none", boxShadow: "0 2px 8px rgba(82,196,26,.35)" }}>{phoneIcon(false)}</button></div>;
}

function formatTime(iso: string | undefined): string {
  if (!iso) return "";
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? "" : fmt.time(date);
}

const META: React.CSSProperties = { fontSize: 11, color: "#bfbfbf", marginTop: 4 };

export function formatBytes(bytes: number): string {
  // Байты — только у совсем маленьких файлов: «1 КБ» ниже килобайта врало бы.
  if (bytes < 1024) return t("unit.b", { value: bytes });
  const { value, unit } = fmt.bytes(bytes);
  return t(unit === "mb" ? "unit.mb" : "unit.kb", { value });
}

export type BubbleAttachment = { name: string; contentType: string; size: number; available: boolean; url: string; inlineUrl: string };

// Фото догружается после появления пузыря: лента, прижатая к низу, доезжает до него.
function scrollFeedToLatest(event: React.SyntheticEvent<HTMLImageElement>) {
  let node: HTMLElement | null = event.currentTarget.parentElement;
  while (node && !(node.scrollHeight > node.clientHeight && /(auto|scroll)/.test(getComputedStyle(node).overflowY))) node = node.parentElement;
  if (node && node.scrollHeight - node.scrollTop - node.clientHeight < 400) node.scrollTop = node.scrollHeight;
}

function AttachmentContent({ attachment, text, light }: { attachment: BubbleAttachment; text: string; light: boolean }) {
  const color = light ? "#fff" : "#262626";
  const muted = light ? "rgba(255,255,255,.75)" : "#8c8c8c";
  const image = /^image\/(jpeg|png|gif|webp)$/.test(attachment.contentType) && attachment.inlineUrl;
  return (
    <div>
      {image
        ? <a href={attachment.inlineUrl} target="_blank" rel="noreferrer" style={{ display: "block", borderRadius: 10, overflow: "hidden", maxWidth: 240 }}><img src={attachment.inlineUrl} alt={attachment.name} onLoad={scrollFeedToLatest} style={{ display: "block", width: "100%", maxHeight: 240, objectFit: "cover" }} /></a>
        : (
          <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 200 }}>
            <span style={{ width: 34, height: 34, flex: "none", display: "inline-flex", alignItems: "center", justifyContent: "center", borderRadius: 9, background: light ? "rgba(255,255,255,.2)" : "#f0f5ff", color: light ? "#fff" : "#1677ff" }}><svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48" /></svg></span>
            <span style={{ display: "flex", flexDirection: "column", minWidth: 0, flex: 1 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{attachment.name}</span>
              <span style={{ fontSize: 11.5, color: muted }}>{attachment.size ? formatBytes(attachment.size) : ""}</span>
            </span>
            {attachment.url ? <a href={attachment.url} download={attachment.name} style={{ fontSize: 12.5, fontWeight: 600, color: light ? "#fff" : "#1677ff", textDecoration: "none", flex: "none" }}>{t("chat.download")}</a> : <span style={{ fontSize: 12, color: muted }}>{t("chat.file_unavailable")}</span>}
          </div>
        )}
      {text && <div style={{ marginTop: 6 }}>{text}</div>}
    </div>
  );
}

export function Bubble({ author, text, accent, time, pendingState, audioUrl, attachment }: { author: "client" | "ai" | "operator"; text: string; accent: string; time?: string; pendingState?: boolean; audioUrl?: string; attachment?: BubbleAttachment }) {
  const at = formatTime(time);
  const content = audioUrl
    ? <audio controls preload="none" src={audioUrl} style={{ width: 216, height: 36, display: "block" }} />
    : attachment
      ? <AttachmentContent attachment={attachment} text={text} light={author === "client"} />
      : text;
  if (author === "client") return <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}><div style={{ maxWidth: "82%" }}><div style={{ background: accent, color: "#fff", borderRadius: "16px 16px 4px 16px", padding: audioUrl ? "8px" : "10px 14px", fontSize: 14.5, lineHeight: 1.5, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{content}</div><div style={{ ...META, marginRight: 4, textAlign: "right" }}>{pendingState ? t("chat.sending_lower") : [at, t("chat.delivered")].filter(Boolean).join(" · ")}</div></div></div>;
  const isOperator = author === "operator";
  return <div style={{ display: "flex", gap: 9, marginBottom: 12 }}><div style={{ width: 30, height: 30, borderRadius: "50%", background: isOperator ? accent : "#eef0f2", border: isOperator ? "none" : "1px solid #e3e6ea", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", flex: "none" }}>{isOperator ? <span style={{ fontSize: 11.5, fontWeight: 600 }}>{t("chat.operator_initial")}</span> : <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#8c8c8c" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="8" r="3.2" /><path d="M5.5 20a6.5 6.5 0 0 1 13 0" /></svg>}</div><div style={{ maxWidth: "82%" }}><div style={{ background: "#fff", border: "1px solid #eee", borderRadius: "16px 16px 16px 4px", padding: audioUrl ? "8px" : "10px 14px", fontSize: 14.5, lineHeight: 1.5, color: "#262626", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{content}</div><div style={{ ...META, marginLeft: 4 }}>{[isOperator ? t("chat.specialist") : t("chat.virtual_assistant"), at].filter(Boolean).join(" · ")}</div></div></div>;
}

function formatPhone(raw: string): string {
  let digits = raw.replace(/\D/g, "");
  if (!digits) return "";
  if (digits.startsWith("8")) digits = "7" + digits.slice(1);
  if (!digits.startsWith("7")) digits = "7" + digits;
  digits = digits.slice(0, 11);
  let out = "+7";
  if (digits.length > 1) out += ` (${digits.slice(1, 4)}`;
  if (digits.length >= 4) out += ")";
  if (digits.length > 4) out += ` ${digits.slice(4, 7)}`;
  if (digits.length > 7) out += `-${digits.slice(7, 9)}`;
  if (digits.length > 9) out += `-${digits.slice(9, 11)}`;
  return out;
}

function PhoneForm({ accent, onSubmit }: { accent: string; onSubmit: (phone: string) => Promise<boolean> }) {
  const [phone, setPhone] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(false);
  const valid = phone.replace(/\D/g, "").length === 11;
  async function submit() { if (!valid || sending) return; setSending(true); setError(false); const ok = await onSubmit(phone); setSending(false); if (!ok) setError(true); }
  return <div style={{ margin: "2px 0 10px 36px", maxWidth: "78%", background: "#fff", border: "1px solid #eee", borderRadius: 12, padding: 12 }}><input type="tel" inputMode="tel" value={phone} onChange={(event) => setPhone(formatPhone(event.target.value))} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); void submit(); } }} placeholder="+7 (___) ___-__-__" style={{ width: "100%", boxSizing: "border-box", height: 38, borderRadius: 8, border: error ? "1px solid #ff4d4f" : "1px solid #d9d9d9", padding: "0 10px", outline: "none", fontSize: 13.5 }} /><button type="button" onClick={() => void submit()} disabled={!valid || sending} style={{ width: "100%", height: 36, marginTop: 8, borderRadius: 8, border: "none", background: valid ? accent : "#d9d9d9", color: "#fff", fontSize: 12.5, fontWeight: 600, cursor: valid ? "pointer" : "default" }}>{sending ? t("chat.sending") : t("chat.share_number")}</button>{error && <div style={{ marginTop: 6, color: "#cf1322", fontSize: 11.5 }}>{t("chat.share_number_failed")}</div>}</div>;
}

export function Typing() {
  return <div style={{ display: "flex", gap: 9, marginBottom: 4 }}><div style={{ width: 30, height: 30, borderRadius: "50%", background: "#eef0f2", border: "1px solid #e3e6ea", display: "flex", alignItems: "center", justifyContent: "center", flex: "none" }}><svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#8c8c8c" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="8" r="3.2" /><path d="M5.5 20a6.5 6.5 0 0 1 13 0" /></svg></div><div style={{ background: "#fff", border: "1px solid #eee", borderRadius: "14px 14px 14px 4px", padding: "12px 14px", display: "flex", alignItems: "center", gap: 5 }}>{[0, 0.2, 0.4].map((delay) => <span key={delay} style={{ width: 6, height: 6, borderRadius: "50%", background: "#b37feb", animation: `wcTyping 1.2s infinite ease-in-out ${delay}s` }} />)}</div></div>;
}

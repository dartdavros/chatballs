import { BotAvatar } from "./BotIcon";
import { useState } from "react";
import { PreparedMessage } from "@chatballs/ui";
import type { MessagePresentation } from "@chatballs/contracts";
import { VoiceMessage } from "./VoiceMessage";
import { AttachmentContent, type BubbleAttachment } from "./ChatAttachment";
import { formatTime } from "./chatFormat";
import { t } from "./i18n";
import { widgetClasses as classes } from "./widgetClasses";
import { AnswerPlayback } from "./speech/AnswerPlayback";
import type { AnswerPlaybackControl } from "./speech/useAnswerPlayback";

export function SystemMessage({ text, neutral = false }: { text: string; neutral?: boolean }) {
  return <div style={{ textAlign: "center", margin: "12px 0" }}><span style={neutral
    ? { display: "inline-block", maxWidth: "92%", padding: "4px 11px", borderRadius: 12, background: "#eceef2", fontSize: 11.5, color: "#8c8c8c", lineHeight: 1.4 }
    : { display: "inline-block", padding: "4px 12px", borderRadius: 20, background: "#e6f4ff", border: "1px solid #91caff", fontSize: 11.5, color: "#0958d9" }}>{text}</span></div>;
}

/** Строка автора над пузырём: аватар и имя — как на утверждённом образце. */
function AuthorRow({ accent, name, operator, avatarUrl }: { accent: string; name: string; operator: boolean; avatarUrl?: string }) {
  const [failedAvatar, setFailedAvatar] = useState<string>();
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
      {operator
        ? <span style={{ width: 32, height: 32, borderRadius: "50%", overflow: "hidden", background: accent, color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", flex: "none", fontSize: 11, fontWeight: 600 }}>{avatarUrl && avatarUrl !== failedAvatar ? <img src={avatarUrl} alt="" onError={() => setFailedAvatar(avatarUrl)} style={{ width: "100%", height: "100%", objectFit: "cover" }} /> : t("chat.operator_initial")}</span>
        : <BotAvatar size={32} accent={accent} />}
      <span style={{ fontSize: 12.5, fontWeight: 600, color: "#595959" }}>{name}</span>
    </div>
  );
}

export function Bubble({ author, authorName, authorAvatarUrl, text, accent, time, pendingState, audioUrl, voice, attachment, snapshot, playback }: { author: "client" | "ai" | "operator"; authorName: string; authorAvatarUrl?: string; text: string; accent: string; time?: string; pendingState?: boolean; audioUrl?: string; voice?: { messageId: number; durationSeconds?: number }; attachment?: BubbleAttachment; snapshot?: MessagePresentation; playback?: { messageId: number; control: AnswerPlaybackControl } }) {
  const at = formatTime(time);
  const content = audioUrl && voice
    ? <VoiceMessage accent={accent} durationSeconds={voice.durationSeconds} light={author === "client"} messageId={voice.messageId} url={audioUrl} />
    : attachment
      ? <AttachmentContent attachment={attachment} text={text} light={author === "client"} />
      : author === "ai" && snapshot && (snapshot.formatVersion !== undefined || snapshot.presentation !== undefined)
        ? <PreparedMessage content={{ ...snapshot, text }} title={t("chat.formatted_message")} /> : text;
  if (author === "client") {
    return (
      <div className={`${classes.message} ${classes.messageClient}`}>
        <div className={classes.messageContent}>
          <div className={`${classes.bubble} ${classes.bubbleClient} ${audioUrl ? classes.bubbleAudio : ""}`} style={{ "--cb-accent": accent } as React.CSSProperties}>{content}</div>
          <div className={classes.messageTime}>{pendingState ? t("chat.sending_lower") : at}</div>
        </div>
      </div>
    );
  }
  const operator = author === "operator";
  return (
    <div className={classes.message}>
      <AuthorRow accent={accent} name={operator ? authorName || t("chat.specialist") : authorName} operator={operator} avatarUrl={authorAvatarUrl} />
      <div className={classes.messageContent}>
        <div className={`${classes.bubble} ${classes.bubbleAgent} ${operator ? classes.bubbleOperator : ""} ${audioUrl ? classes.bubbleAudio : ""}`}>{content}{playback && <AnswerPlayback control={playback.control} messageId={playback.messageId} text={text} />}</div>
      </div>
    </div>
  );
}

export function Typing({ accent, authorName }: { accent: string; authorName: string }) {
  return (
    <div style={{ marginBottom: 6 }}>
      <AuthorRow accent={accent} name={authorName} operator={false} />
      <div style={{ display: "inline-flex", alignItems: "center", gap: 7, background: "#fff", border: "1px solid #eee", borderRadius: "4px 16px 16px 16px", padding: "11px 15px" }}>
        <span style={{ fontSize: 12.5, color: "#8c8c8c" }}>{t("chat.typing")}</span>
        <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
          {[0, 0.2, 0.4].map((delay) => <span key={delay} style={{ width: 6, height: 6, borderRadius: "50%", background: accent, animation: `wcTyping 1.2s infinite ease-in-out ${delay}s` }} />)}
        </span>
      </div>
    </div>
  );
}

import { useState } from "react";
import { authorAvatarUrl, attachmentUrl, MAX_FILE_BYTES, voiceAudioUrl } from "./api";
import { BrandFooter } from "./BrandFooter";
import { CallInviteBanner, ChatBody, ChatComposer, ChatHeader, StartChatFooter } from "./ChatView";
import { usePanelFullscreen } from "./usePanelFullscreen";
import { useChatSession } from "./useChatSession";
import { resolveWidgetAppearance } from "./widgetAppearance";
import { WidgetStyles } from "./WidgetStyles";
import { widgetClasses as classes } from "./widgetClasses";
import { t } from "./i18n";
import { PreChatForm } from "./PreChatForm";

function closePanel() {
  window.parent.postMessage({ type: "chatballs-chat-close" }, "*");
}

/** Размер окна держит лоадер: панель живёт в iframe и сама себя не растянет. */
function requestExpanded(expanded: boolean) {
  window.parent.postMessage({ type: "chatballs-chat-expand", expanded }, "*");
}

export function App() {
  const { playback, config, state, accepted, siteValues, siteEvent, messages, ratingRequests, pending, awaiting, thinking, call, input, setInput, starting, recorder, dictation, bodyRef, token, lastContactRequestId, showPhoneForm, unavailable, accept, send, submitContact, acceptCallInvite, declineCallInvite, attachment, attachmentError, setAttachment, setAttachmentError } = useChatSession();
  const [expanded, setExpanded] = useState(false);
  const fullscreen = usePanelFullscreen();
  const { accent, headerIcon, customCss } = resolveWidgetAppearance(config);
  const title = config?.title || t("chat.chat");

  const showPreChat = Boolean(config?.available && config.preChat?.enabled && !accepted);

  function toggleExpanded() {
    setExpanded((previous) => {
      requestExpanded(!previous);
      return !previous;
    });
  }

  return (
    <div className={classes.root} style={{ "--cb-accent": accent } as React.CSSProperties}>
      <WidgetStyles customCss={customCss} />
      <ChatHeader icon={headerIcon} accent={accent} title={title} expanded={expanded} canExpand={!fullscreen} onToggleExpand={toggleExpanded} onClose={closePanel} />
      {showPreChat && config ? <PreChatForm config={config} accent={accent} title={title} siteValues={siteValues} starting={starting} onAccept={accept} /> : <ChatBody playback={playback} bodyRef={bodyRef} siteEvent={siteEvent} config={config} unavailable={unavailable} accepted={accepted} accent={accent} title={title} messages={messages} ratingRequests={ratingRequests} pending={pending} awaiting={thinking && state === "ai"} state={state} lastContactRequestId={lastContactRequestId} showPhoneForm={showPhoneForm} onSubmitContact={submitContact} authorAvatarUrlFor={token ? (id) => authorAvatarUrl(token, id) : undefined} audioUrlFor={token ? (id) => voiceAudioUrl(token, id) : undefined} attachmentUrlFor={token ? (id, inline) => attachmentUrl(token, id, inline) : undefined} />}
      {config?.available && accepted && call && (call.status === "REQUESTED" || call.status === "RINGING") && <CallInviteBanner call={call} accent={accent} onAccept={() => void acceptCallInvite()} onDecline={() => void declineCallInvite()} />}
      {config?.available && !accepted && !showPreChat && <StartChatFooter accent={accent} starting={starting} onAccept={() => void accept()} />}
      {config?.available && accepted && <ChatComposer accent={accent} input={input} onInput={setInput} onSend={() => void send()} dictation={config.speech?.microphoneMode === "dictation" ? dictation : undefined} voice={config.features?.voiceMessages === false ? undefined : recorder} attachment={{ file: attachment, errorText: attachmentError, pick: (file) => { if (!file) return; if (file.size > MAX_FILE_BYTES) { setAttachmentError(t("chat.file_too_big")); return; } setAttachmentError(""); setAttachment(file); }, clear: () => setAttachment(null) }} />}
      {config?.available && <BrandFooter accent={accent} />}
    </div>
  );
}

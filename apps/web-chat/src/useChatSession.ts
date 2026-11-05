import { useEffect, useRef, useState } from "react";

import {
  declineWebchatCall,
  getConfig,
  openWebchatCall,
  poll,
  sendContact,
  sendMessage,
  sendFile,
  sendVoice,
  type CallInfo,
  type Poll,
  type WebConfig,
  type WebMessage,
} from "./api";
import { useScrollToLatest } from "./useScrollToLatest";
import { useWidgetConsent } from "./useWidgetConsent";
import { useChatPolling } from "./useChatPolling";
import { useVoiceRecorder } from "./useVoiceRecorder";
import { useDictation } from "./speech/useDictation";
import { useAnswerPlayback } from "./speech/useAnswerPlayback";
import { appendDictation } from "./speech/draft";
import { useWidgetActivity } from "./widgetActivity";
import { useVisitorSignals } from "./useVisitorSignals";
import { applyWidgetLanguage, t } from "./i18n";
import type { RatingRequest } from "./ratings/api";
import { useSiteEvents } from "./proactivity/useSiteEvents";

const PARAMS = new URLSearchParams(location.search);
const WIDGET_KEY = PARAMS.get("widgetKey") || "";
const LEGACY_CHANNEL = PARAMS.get("channel") || "";
const ENTRY = WIDGET_KEY ? { widgetKey: WIDGET_KEY } : { channel: LEGACY_CHANNEL };
const HOST_ORIGIN = document.referrer ? new URL(document.referrer).origin : location.origin;
const TOKEN_KEY = `chatballs-chat-token:${WIDGET_KEY || `channel:${LEGACY_CHANNEL}`}`;

export function useChatSession() {
  const [config, setConfig] = useState<WebConfig | null>(null);
  function reloadConfig() {
    return getConfig(ENTRY, HOST_ORIGIN).then(loaded => { applyWidgetLanguage(loaded.language); setConfig(loaded); });
  }
  const refreshConfig = () => { void reloadConfig().catch(() => undefined); };
  const { token, accepted, consentReady, starting, accept, forgetConsent, invalidateConsent, siteValues } = useWidgetConsent(config, ENTRY, HOST_ORIGIN, TOKEN_KEY, refreshConfig);
  const siteEvent = useSiteEvents({ config, token, accepted, consentReady, widgetKey: WIDGET_KEY, hostOrigin: HOST_ORIGIN });
  useVisitorSignals(accepted ? token : null, HOST_ORIGIN);
  const [messages, setMessages] = useState<WebMessage[]>([]);
  const [ratingRequests, setRatingRequests] = useState<RatingRequest[]>([]);
  const [pending, setPending] = useState<string[]>([]);
  const [state, setState] = useState<"ai" | "operator" | "waiting">("ai");
  const [awaiting, setAwaiting] = useState(false);
  // Ответ считается на сервере и приедет следующим опросом: до тех пор в ленте
  // висит «печатает».
  const [thinking, setThinking] = useState(false);
  const [input, setInput] = useState("");
  const [contactSent, setContactSent] = useState(false);
  const [attachment, setAttachment] = useState<File | null>(null);
  const [attachmentError, setAttachmentError] = useState("");
  const [call, setCall] = useState<CallInfo | null>(null);
  const lastId = useRef(0);
  const openedCallId = useRef("");
  const pollingReady = useRef(false);
  const bodyRef = useRef<HTMLDivElement>(null);
  const scrollToLatest = useScrollToLatest(bodyRef);
  const incomingCall = Boolean(call && (call.status === "REQUESTED" || call.status === "RINGING"));
  const notifyNewMessage = useWidgetActivity(incomingCall);
  const playback = useAnswerPlayback(accepted ? token : null, config?.speech?.playbackAvailable ? config.speech.ttsRevision ?? "" : "", HOST_ORIGIN);
  const dictation = useDictation({
    token: accepted ? token : null, hostOrigin: HOST_ORIGIN, settings: config?.speech,
    onResult: (text) => setInput((current) => appendDictation(current, text)),
  });
  const recorder = useVoiceRecorder({
    maxBytes: config?.speech?.maxRecordingBytes,
    onSend: async (audio, durationSeconds) => {
      if (!token) return;
      const ok = await sendVoice(token, audio, durationSeconds, HOST_ORIGIN);
      if (!ok) throw new Error(t("chat.could_not_send_voice"));
      try { ingestPoll(await poll(token, lastId.current)); } catch { /* polling loop will retry */ }
    },
  });

  useEffect(() => {
    void reloadConfig().catch(() => setConfig({ available: false }));
  }, []);

  function ingestPoll(data: Poll, notify = true) {
    if (data.playback?.consentCurrent === false) {
      playback.clear();
      dictation.cancel();
      invalidateConsent();
      refreshConfig();
    }
    siteEvent.updateStatus(data.siteEvent);
    setRatingRequests(data.ratingRequests || []);
    // Диалог удалили на стороне поддержки — переписка обнуляется, и виджет
    // продолжает жить как только что открытый.
    if (data.reset) {
      dictation.cancel();
      playback.clear();
      lastId.current = 0;
      setMessages([]);
      setPending([]);
      setAwaiting(false);
      setContactSent(false);
    }
    setState(data.state);
    if (data.playback) setConfig(previous => previous && previous.speech
      && (previous.speech.ttsRevision !== data.playback!.ttsRevision || previous.speech.playbackAvailable !== data.playback!.playbackAvailable)
      ? { ...previous, speech: { ...previous.speech, ...data.playback } } : previous);
    if (data.autonomous !== undefined) setConfig((previous) => previous && previous.autonomous !== data.autonomous
      ? { ...previous, autonomous: data.autonomous } : previous);
    setThinking(Boolean(data.thinking));
    setCall(data.call?.callId === openedCallId.current ? null : (data.call ?? null));
    if (!data.messages.length) return;
    if (notify && data.messages.some((message) => message.author === "ai" || message.author === "operator")) notifyNewMessage();
    lastId.current = Math.max(lastId.current, ...data.messages.map((message) => message.id));
    setMessages((previous) => [...previous, ...data.messages.filter((message) => !previous.some((existing) => existing.id === message.id))]);
    if (data.messages.some((message) => message.author !== "client")) setAwaiting(false);
    setPending([]);
  }

  useChatPolling(accepted ? token : null, lastId, pollingReady, ingestPoll, forgetSession);

  useEffect(() => {
    scrollToLatest();
  }, [scrollToLatest, messages, pending, awaiting]);

  function forgetSession() {
    playback.clear();
    setRatingRequests([]);
    forgetConsent();
    lastId.current = 0;
    pollingReady.current = false;
    setMessages([]);
    setPending([]);
    setAwaiting(false);
    setThinking(false);
    setCall(null);
    setContactSent(false);
  }

  async function send() {
    const text = input.trim();
    if ((!text && !attachment) || !token || !accepted || awaiting || dictation.busy || text.length > 4000) return;
    siteEvent.cancel();
    setInput("");
    const file = attachment;
    setAttachment(null);
    setAttachmentError("");
    setPending((previous) => [...previous, file ? `${file.name}${text ? ` · ${text}` : ""}` : text]);
    setAwaiting(true);
    if (file) {
      const ok = await sendFile(token, file, text).catch(() => false);
      if (!ok) setAttachmentError(t("chat.could_not_send_file"));
    } else {
      const ok = await sendMessage(token, text).catch(() => false);
      if (!ok) setInput((current) => current ? appendDictation(text, current) : text);
    }
    try { ingestPoll(await poll(token, lastId.current)); } catch { /* polling loop will retry */ }
    setPending([]);
    setAwaiting(false);
  }

  async function submitContact(phone: string): Promise<boolean> {
    if (!token) return false;
    const ok = await sendContact(token, phone).catch(() => false);
    if (ok) {
      setContactSent(true);
      try { ingestPoll(await poll(token, lastId.current)); } catch { /* polling loop will retry */ }
    }
    return ok;
  }

  async function acceptCallInvite() {
    if (!token) return;
    const opened = await openWebchatCall(token).catch(() => null);
    if (!opened) { setCall(null); return; }
    openedCallId.current = opened.call.callId;
    setCall(null);
    window.open(`/calls/${opened.call.callId}?kind=${opened.call.kind}#${opened.accessToken}`, "_blank", "noopener");
  }

  async function declineCallInvite() {
    if (!token) return;
    await declineWebchatCall(token).catch(() => undefined);
    setCall(null);
  }

  const lastContactRequestId = messages.reduce((current, message) => message.kind === "contact_request" ? message.id : current, 0);
  const showPhoneForm = lastContactRequestId > 0 && !(contactSent || messages.some((message) => message.kind === "contact"));
  const unavailable = config !== null && !config.available;

  return { playback, config, state, accepted, siteValues, siteEvent, messages, ratingRequests, pending, awaiting, thinking, call, input, setInput, starting, recorder, dictation, bodyRef, token, lastContactRequestId, showPhoneForm, unavailable, accept, send, submitContact, acceptCallInvite, declineCallInvite, attachment, attachmentError, setAttachment, setAttachmentError };
}

import { useEffect, useRef, useState } from "react";

import {
  declineWebchatCall,
  getConfig,
  openWebchatCall,
  poll,
  sendContact,
  sendMessage,
  startSession,
  type CallInfo,
  type Poll,
  type WebConfig,
  type WebMessage,
} from "./api";
import { CallInviteBanner, ChatBody, ChatComposer, ChatHeader, StartChatFooter } from "./ChatView";
import { useScrollToLatest } from "./useScrollToLatest";
import { useWidgetActivity } from "./widgetActivity";

const CHANNEL = new URLSearchParams(location.search).get("channel") || "edevs";
const TOKEN_KEY = `edevs-chat-token:${CHANNEL}`;

function closePanel() {
  window.parent.postMessage({ type: "edevs-chat-close" }, "*");
}

export function App() {
  const [config, setConfig] = useState<WebConfig | null>(null);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [accepted, setAccepted] = useState<boolean>(() => Boolean(localStorage.getItem(TOKEN_KEY)));
  const [messages, setMessages] = useState<WebMessage[]>([]);
  const [pending, setPending] = useState<string[]>([]);
  const [state, setState] = useState<"ai" | "operator" | "waiting">("ai");
  const [awaiting, setAwaiting] = useState(false);
  const [input, setInput] = useState("");
  const [starting, setStarting] = useState(false);
  const [contactSent, setContactSent] = useState(false);
  const [call, setCall] = useState<CallInfo | null>(null);
  const lastId = useRef(0);
  const openedCallId = useRef("");
  const pollingReady = useRef(false);
  const bodyRef = useRef<HTMLDivElement>(null);
  const scrollToLatest = useScrollToLatest(bodyRef);
  const incomingCall = Boolean(call && (call.status === "REQUESTED" || call.status === "RINGING"));
  const notifyNewMessage = useWidgetActivity(incomingCall);

  useEffect(() => {
    getConfig(CHANNEL).then(setConfig).catch(() => setConfig({ available: false }));
  }, []);

  function ingestPoll(data: Poll, notify = true) {
    setState(data.state);
    setCall(data.call?.callId === openedCallId.current ? null : (data.call ?? null));
    if (!data.messages.length) return;
    if (notify && data.messages.some((message) => message.author === "ai" || message.author === "operator")) notifyNewMessage();
    lastId.current = Math.max(lastId.current, ...data.messages.map((message) => message.id));
    setMessages((previous) => [...previous, ...data.messages.filter((message) => !previous.some((existing) => existing.id === message.id))]);
    if (data.messages.some((message) => message.author !== "client")) setAwaiting(false);
    setPending([]);
  }

  useEffect(() => {
    if (!accepted || !token) return;
    let alive = true;
    const tick = async () => {
      try {
        const data = await poll(token, lastId.current);
        if (alive) {
          ingestPoll(data, pollingReady.current);
          pollingReady.current = true;
        }
      } catch {
        /* keep trying */
      }
    };
    void tick();
    const timer = setInterval(tick, 2500);
    return () => { alive = false; clearInterval(timer); };
  }, [accepted, token]);

  useEffect(() => {
    scrollToLatest();
  }, [scrollToLatest, messages, pending, awaiting]);

  const accent = config?.accent || "#1677ff";
  const title = config?.title || "Чат";
  const letter = title.trim()[0]?.toUpperCase() || "E";

  async function accept() {
    setStarting(true);
    const nextToken = await startSession(CHANNEL);
    setStarting(false);
    if (!nextToken) return;
    localStorage.setItem(TOKEN_KEY, nextToken);
    setToken(nextToken);
    setAccepted(true);
  }

  async function send() {
    const text = input.trim();
    if (!text || !token || awaiting) return;
    setInput("");
    setPending((previous) => [...previous, text]);
    setAwaiting(true);
    await sendMessage(token, text).catch(() => undefined);
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
  const status = state === "operator"
    ? { label: "Отвечает специалист", dot: "#52c41a" }
    : state === "waiting"
      ? { label: "Передаём оператору", dot: "#faad14" }
      : { label: "Виртуальный помощник", dot: "#52c41a" };
  const unavailable = config !== null && !config.available;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", width: "100%", background: "#fff", fontFamily: "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif", color: "#1f1f1f", overflow: "hidden" }}>
      <ChatHeader accent={accent} letter={letter} title={title} statusLabel={status.label} statusDot={status.dot} unavailable={unavailable} onClose={closePanel} />
      <ChatBody bodyRef={bodyRef} config={config} unavailable={unavailable} accepted={accepted} accent={accent} letter={letter} title={title} messages={messages} pending={pending} awaiting={awaiting} lastContactRequestId={lastContactRequestId} showPhoneForm={showPhoneForm} onSubmitContact={submitContact} />
      {config?.available && accepted && call && (call.status === "REQUESTED" || call.status === "RINGING") && <CallInviteBanner call={call} accent={accent} onAccept={() => void acceptCallInvite()} onDecline={() => void declineCallInvite()} />}
      {config?.available && !accepted && <StartChatFooter accent={accent} starting={starting} onAccept={() => void accept()} />}
      {config?.available && accepted && <ChatComposer accent={accent} state={state} quickReplies={config.quickReplies ?? []} pendingCount={pending.length} messageCount={messages.length} input={input} onInput={setInput} onSend={() => void send()} />}
    </div>
  );
}

import { useEffect, useRef, useState } from "react";

import { pollSupport, sendSupport, startSupportSession, type WebMessage } from "./api";
import { Bubble, ChatComposer, ChatHeader, SystemMessage, Typing } from "./ChatView";
import { SUPPORT_ACCENT, SupportStatusScreen, supportShell } from "./SupportStatusScreen";
import { useScrollToLatest } from "./useScrollToLatest";
import { useWidgetActivity } from "./widgetActivity";

// Support-режим виджета (SPEC-HUB-0010 §7): authenticated in-product чат.
// Нет consent/lead form, нет полей имя/email/purchase — клиент уже авторизован
// в продукте. Product Support Token запрашивается у host через loader runtime API.
const PARAMS = new URLSearchParams(location.search);
const WIDGET_KEY = PARAMS.get("widgetKey") || "";
const INSTANCE_ID = PARAMS.get("instanceId") || "";
const HOST_ORIGIN = document.referrer ? new URL(document.referrer).origin : location.origin;

function requestSupportToken(): Promise<string> {
  return new Promise((resolve, reject) => {
    const requestId = `token_${crypto.randomUUID()}`;
    const timeout = window.setTimeout(() => {
      window.removeEventListener("message", receive);
      reject(new Error("Support token provider timed out"));
    }, 10000);
    function receive(event: MessageEvent) {
      const data = event.data ?? {};
      if (
        event.source !== window.parent
        || event.origin !== HOST_ORIGIN
        || data.type !== "chatbolls-chat-token-response"
        || data.instanceId !== INSTANCE_ID
        || data.requestId !== requestId
      ) return;
      window.clearTimeout(timeout);
      window.removeEventListener("message", receive);
      if (typeof data.token === "string" && data.token) resolve(data.token);
      else reject(new Error("Support token unavailable"));
    }
    window.addEventListener("message", receive);
    window.parent.postMessage({
      type: "chatbolls-chat-token-request",
      instanceId: INSTANCE_ID,
      requestId,
      widgetKey: WIDGET_KEY,
    }, HOST_ORIGIN);
  });
}

function closePanel() {
  window.parent.postMessage({ type: "edevs-chat-close" }, "*");
}

export function SupportApp() {
  const [session, setSession] = useState<Awaited<ReturnType<typeof startSupportSession>>>(null);
  const [failed, setFailed] = useState(false);
  const [messages, setMessages] = useState<WebMessage[]>([]);
  const [pending, setPending] = useState<string[]>([]);
  const [state, setState] = useState<"ai" | "operator" | "waiting">("ai");
  const [awaiting, setAwaiting] = useState(false);
  const [input, setInput] = useState("");
  const lastId = useRef(0);
  const bodyRef = useRef<HTMLDivElement>(null);
  const scrollToLatest = useScrollToLatest(bodyRef);
  const notifyNewMessage = useWidgetActivity(false);

  // Старт сессии один раз (SPEC §7.2: нет consent/accept flow).
  useEffect(() => {
    let alive = true;
    if (!WIDGET_KEY || !INSTANCE_ID) {
      setFailed(true);
      return;
    }
    requestSupportToken()
      .then((token) => startSupportSession(WIDGET_KEY, token, HOST_ORIGIN))
      .then((s) => {
        if (!alive) return;
        if (!s) {
          setFailed(true);
          return;
        }
        setSession(s);
        if (s.conversation.messages.length) {
          lastId.current = Math.max(...s.conversation.messages.map((m) => m.id));
          setMessages(s.conversation.messages);
        }
        setState(modeOf(s.conversation.controlMode));
      })
      .catch(() => alive && setFailed(true));
    return () => {
      alive = false;
    };
  }, []);

  // Polling ответов AI/оператора.
  useEffect(() => {
    if (!session) return;
    let alive = true;
    const tick = async () => {
      try {
        const data = await pollSupport(session.widgetCredential, lastId.current);
        if (!alive) return;
        setState(data.state);
        if (data.messages.length) {
          if (data.messages.some((m) => m.author === "ai" || m.author === "operator")) notifyNewMessage();
          lastId.current = Math.max(lastId.current, ...data.messages.map((m) => m.id));
          setMessages((prev) => [...prev, ...data.messages.filter((m) => !prev.some((p) => p.id === m.id))]);
          if (data.messages.some((m) => m.author !== "client")) setAwaiting(false);
          setPending([]);
        }
      } catch {
        /* keep trying */
      }
    };
    void tick();
    const timer = setInterval(tick, 2500);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [session]);

  useEffect(() => {
    scrollToLatest();
  }, [scrollToLatest, messages, pending, awaiting]);

  async function send() {
    const text = input.trim();
    if (!text || !session || awaiting) return;
    setInput("");
    setPending((p) => [...p, text]);
    setAwaiting(true);
    await sendSupport(session.widgetCredential, text).catch(() => undefined);
    try {
      const data = await pollSupport(session.widgetCredential, lastId.current);
      setState(data.state);
      if (data.messages.length) {
        if (data.messages.some((m) => m.author === "ai" || m.author === "operator")) notifyNewMessage();
        lastId.current = Math.max(lastId.current, ...data.messages.map((m) => m.id));
        setMessages((prev) => [...prev, ...data.messages.filter((m) => !prev.some((p) => p.id === m.id))]);
        setAwaiting(false);
        setPending([]);
      }
    } catch {
      /* polling loop will retry */
    }
  }

  const displayName = session?.snapshot.displayName || "";
  const accent = SUPPORT_ACCENT;
  const status = state === "operator"
    ? { label: "Отвечает специалист", dot: "#52c41a" }
    : state === "waiting"
      ? { label: "Передаём оператору", dot: "#faad14" }
      : { label: "Виртуальный помощник", dot: "#52c41a" };

  if (failed) return <SupportStatusScreen failed />;
  if (!session) return <SupportStatusScreen failed={false} />;

  const greeting = displayName ? `Здравствуйте, ${displayName.split(" ")[0]}.` : "Здравствуйте.";

  return (
    <div style={supportShell()}>
      <ChatHeader accent={accent} letter="П" title="Поддержка" statusLabel={status.label} statusDot={status.dot} unavailable={false} onClose={closePanel} />

      <div ref={bodyRef} style={{ flex: 1, minHeight: 0, overflowY: "auto", background: "#f7f8fa", padding: "18px 16px" }}>
        <div style={{ textAlign: "center", marginBottom: 14 }}>
          <span style={{ display: "inline-block", padding: "3px 11px", borderRadius: 20, background: "#eef0f2", fontSize: 11, color: "#8c8c8c" }}>Сегодня</span>
        </div>
        <Bubble author="ai" text={greeting + " Чем помочь?"} accent={accent} />
        {messages.map((m) => (m.author === "system"
          ? <SystemMessage key={m.id} text={m.text} />
          : <Bubble key={m.id} author={m.author} text={m.text} accent={accent} time={m.createdAt} />))}
        {pending.map((t, i) => <Bubble key={`p${i}`} author="client" text={t} accent={accent} pendingState />)}
        {awaiting && <Typing />}
      </div>

      <ChatComposer accent={accent} state={state} quickReplies={[]} pendingCount={pending.length} messageCount={messages.length} input={input} placeholder="Опишите вопрос…" onInput={setInput} onSend={() => void send()} />
    </div>
  );
}

function modeOf(controlMode: string): "ai" | "operator" | "waiting" {
  if (controlMode === "HUMAN") return "operator";
  if (controlMode === "PAUSED") return "waiting";
  return "ai";
}

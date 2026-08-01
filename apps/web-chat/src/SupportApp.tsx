import { useEffect, useRef, useState } from "react";

import { pollSupport, sendSupport, startSupportSession, type WebMessage } from "./api";
import { Bubble, ChatComposer, ChatHeader, SystemMessage, Typing } from "./ChatView";
import { useScrollToLatest } from "./useScrollToLatest";
import { useWidgetActivity } from "./widgetActivity";

// Support-режим виджета (SPEC-HUB-0010 §7): authenticated in-product чат.
// Нет consent/lead form, нет полей имя/email/purchase — клиент уже авторизован
// в продукте. Старт по Product Support Token (data-support-token в loader).
const CHANNEL = new URLSearchParams(location.search).get("channel") || "";
const TOKEN = new URLSearchParams(location.search).get("token") || "";
const DEFAULT_ACCENT = "#1677ff";

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
    if (!CHANNEL || !TOKEN) {
      setFailed(true);
      return;
    }
    startSupportSession(CHANNEL, TOKEN)
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
  const accent = DEFAULT_ACCENT;
  const status = state === "operator"
    ? { label: "Отвечает специалист", dot: "#52c41a" }
    : state === "waiting"
      ? { label: "Передаём оператору", dot: "#faad14" }
      : { label: "Виртуальный помощник", dot: "#52c41a" };

  const header = (statusLabel: string, dot: string) => (
    <ChatHeader accent={accent} letter="П" title="Поддержка" statusLabel={statusLabel} statusDot={dot} unavailable={false} onClose={closePanel} />
  );

  if (failed) {
    return (
      <div style={shell()}>
        {header("Временно недоступна", "#faad14")}
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", background: "#f7f8fa" }}>
          <p style={{ color: "#595959", fontSize: 13, padding: 24, textAlign: "center" }}>Поддержка временно недоступна. Обновите страницу или обратитесь позже.</p>
        </div>
      </div>
    );
  }

  if (!session) {
    return (
      <div style={shell()}>
        {header("Подключение…", "#52c41a")}
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", background: "#f7f8fa" }}>
          <span style={{ color: "#8c8c8c", fontSize: 13 }}>Загрузка…</span>
        </div>
      </div>
    );
  }

  const greeting = displayName ? `Здравствуйте, ${displayName.split(" ")[0]}.` : "Здравствуйте.";

  return (
    <div style={shell()}>
      {header(status.label, status.dot)}

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

function shell(): React.CSSProperties {
  return { display: "flex", flexDirection: "column", height: "100%", width: "100%", background: "#fff", fontFamily: "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif", color: "#1f1f1f", overflow: "hidden" };
}

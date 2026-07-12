import { useEffect, useRef, useState } from "react";

import { pollSupport, sendSupport, startSupportSession, type WebMessage } from "./api";
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
    const node = bodyRef.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [messages, pending, awaiting]);

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

  if (failed) {
    return (
      <div style={shell(accent)}>
        <Header accent={accent} title="Поддержка" statusLabel="Временно недоступна" dot="#faad14" />
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", background: "#f7f8fa" }}>
          <p style={{ color: "#595959", fontSize: 13, padding: 24, textAlign: "center" }}>Поддержка временно недоступна. Обновите страницу или обратитесь позже.</p>
        </div>
      </div>
    );
  }

  if (!session) {
    return (
      <div style={shell(accent)}>
        <Header accent={accent} title="Поддержка" statusLabel="Подключение…" dot="#52c41a" />
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", background: "#f7f8fa" }}>
          <span style={{ color: "#8c8c8c", fontSize: 13 }}>Загрузка…</span>
        </div>
      </div>
    );
  }

  const greeting = displayName ? `Здравствуйте, ${displayName.split(" ")[0]}.` : "Здравствуйте.";

  return (
    <div style={shell(accent)}>
      <Header accent={accent} title="Поддержка" statusLabel={status.label} dot={status.dot} />

      <div ref={bodyRef} style={{ flex: 1, minHeight: 0, overflowY: "auto", background: "#f7f8fa", padding: "16px 14px" }}>
        <div style={{ textAlign: "center", marginBottom: 14 }}>
          <span style={{ display: "inline-block", padding: "3px 11px", borderRadius: 20, background: "#eef0f2", fontSize: 11, color: "#8c8c8c" }}>Сегодня</span>
        </div>
        <Bubble author="ai" text={greeting + " Чем помочь?"} accent={accent} />
        {messages.map((m) => (m.author === "system"
          ? <div key={m.id} style={{ textAlign: "center", margin: "12px 0" }}><span style={{ display: "inline-block", padding: "4px 12px", borderRadius: 20, background: "#e6f4ff", border: "1px solid #91caff", fontSize: 11.5, color: "#0958d9" }}>{m.text}</span></div>
          : <Bubble key={m.id} author={m.author} text={m.text} accent={accent} />))}
        {pending.map((t, i) => <Bubble key={`p${i}`} author="client" text={t} accent={accent} pendingState />)}
        {awaiting && <Typing />}
      </div>

      <div style={{ flex: "none", background: "#fff", borderTop: "1px solid #f0f0f0", padding: "10px 12px 12px" }}>
        <div style={{ display: "flex", alignItems: "flex-end", gap: 8, border: "1px solid #e8e8e8", borderRadius: 12, padding: "6px 6px 6px 12px", background: "#fff" }}>
          <textarea
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void send(); } }}
            placeholder="Опишите вопрос…"
            style={{ flex: 1, border: "none", outline: "none", resize: "none", fontSize: 13.5, lineHeight: 1.5, color: "#262626", fontFamily: "inherit", padding: "6px 0", maxHeight: 90 }}
          />
          <button onClick={() => void send()} aria-label="Отправить" style={{ width: 34, height: 34, borderRadius: 8, border: "none", background: accent, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", flex: "none" }}>
            <svg viewBox="0 0 24 24" width={16} height={16} fill="none" stroke="#fff" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></svg>
          </button>
        </div>
      </div>
    </div>
  );
}

function modeOf(controlMode: string): "ai" | "operator" | "waiting" {
  if (controlMode === "HUMAN") return "operator";
  if (controlMode === "PAUSED") return "waiting";
  return "ai";
}

function shell(accent: string): React.CSSProperties {
  return { display: "flex", flexDirection: "column", height: "100%", width: "100%", background: "#fff", fontFamily: "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif", color: "#1f1f1f", overflow: "hidden" };
}

function Header({ accent, title, statusLabel, dot }: { accent: string; title: string; statusLabel: string; dot: string }) {
  return (
    <div style={{ flex: "none", background: accent, padding: "14px 16px", display: "flex", alignItems: "center", gap: 11 }}>
      <div style={{ width: 36, height: 36, borderRadius: 10, background: "rgba(255,255,255,0.18)", display: "flex", alignItems: "center", justifyContent: "center", flex: "none", fontSize: 15, fontWeight: 700, color: "#fff" }}>П</div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 14.5, fontWeight: 600, color: "#fff", lineHeight: 1.2 }}>{title}</div>
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 2 }}>
          <span style={{ width: 7, height: 7, borderRadius: "50%", background: dot, flex: "none" }} />
          <span style={{ fontSize: 11.5, color: "rgba(255,255,255,0.92)" }}>{statusLabel}</span>
        </div>
      </div>
      <button onClick={closePanel} aria-label="Свернуть" style={{ width: 30, height: 30, borderRadius: 8, border: "none", background: "rgba(255,255,255,0.14)", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", flex: "none" }}>
        <svg viewBox="0 0 24 24" width={17} height={17} fill="none" stroke="#fff" strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round"><line x1="5" y1="12" x2="19" y2="12" /></svg>
      </button>
    </div>
  );
}

function Bubble({ author, text, accent, pendingState }: { author: "client" | "ai" | "operator"; text: string; accent: string; pendingState?: boolean }) {
  if (author === "client") {
    return (
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 10 }}>
        <div style={{ maxWidth: "78%" }}>
          <div style={{ background: accent, color: "#fff", borderRadius: "14px 14px 4px 14px", padding: "9px 13px", fontSize: 13.5, lineHeight: 1.45, whiteSpace: "pre-wrap" }}>{text}</div>
          <div style={{ fontSize: 10.5, color: "#bfbfbf", margin: "3px 4px 0 0", textAlign: "right" }}>{pendingState ? "отправка…" : "доставлено"}</div>
        </div>
      </div>
    );
  }
  const isOperator = author === "operator";
  return (
    <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
      <div style={{ width: 28, height: 28, borderRadius: "50%", background: isOperator ? accent : "#eef0f2", border: isOperator ? "none" : "1px solid #e3e6ea", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", flex: "none" }}>
        {isOperator ? <span style={{ fontSize: 11, fontWeight: 600 }}>О</span> : <svg viewBox="0 0 24 24" width={15} height={15} fill="none" stroke="#8c8c8c" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="8" r="3.2" /><path d="M5.5 20a6.5 6.5 0 0 1 13 0" /></svg>}
      </div>
      <div style={{ maxWidth: "78%" }}>
        <div style={{ background: "#fff", border: "1px solid #eee", borderRadius: "14px 14px 14px 4px", padding: "9px 13px", fontSize: 13.5, lineHeight: 1.45, color: "#262626", whiteSpace: "pre-wrap" }}>{text}</div>
        <div style={{ fontSize: 10.5, color: "#bfbfbf", margin: "3px 0 0 4px" }}>{isOperator ? "Специалист" : "Виртуальный помощник"}</div>
      </div>
    </div>
  );
}

function Typing() {
  return (
    <div style={{ display: "flex", gap: 8, marginBottom: 4 }}>
      <div style={{ width: 28, height: 28, borderRadius: "50%", background: "#eef0f2", border: "1px solid #e3e6ea", display: "flex", alignItems: "center", justifyContent: "center", flex: "none" }}>
        <svg viewBox="0 0 24 24" width={15} height={15} fill="none" stroke="#8c8c8c" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="8" r="3.2" /><path d="M5.5 20a6.5 6.5 0 0 1 13 0" /></svg>
      </div>
      <div style={{ background: "#fff", border: "1px solid #eee", borderRadius: "14px 14px 14px 4px", padding: "12px 14px", display: "flex", alignItems: "center", gap: 5 }}>
        {[0, 0.2, 0.4].map((d) => <span key={d} style={{ width: 6, height: 6, borderRadius: "50%", background: "#b37feb", animation: `wcTyping 1.2s infinite ease-in-out ${d}s` }} />)}
      </div>
    </div>
  );
}

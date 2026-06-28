import { useEffect, useRef, useState } from "react";

import { getConfig, poll, sendMessage, startSession, type WebConfig, type WebMessage } from "./api";

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
  const lastId = useRef(0);
  const bodyRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getConfig(CHANNEL).then(setConfig).catch(() => setConfig({ available: false }));
  }, []);

  function ingestPoll(data: { state: "ai" | "operator" | "waiting"; messages: WebMessage[] }) {
    setState(data.state);
    if (data.messages.length) {
      lastId.current = Math.max(lastId.current, ...data.messages.map((m) => m.id));
      setMessages((prev) => [...prev, ...data.messages.filter((m) => !prev.some((p) => p.id === m.id))]);
      if (data.messages.some((m) => m.author !== "client")) setAwaiting(false);
      setPending([]);
    }
  }

  // Поллинг ответов AI/оператора.
  useEffect(() => {
    if (!accepted || !token) return;
    let alive = true;
    const tick = async () => {
      try {
        const data = await poll(token, lastId.current);
        if (alive) ingestPoll(data);
      } catch {
        /* keep trying */
      }
    };
    void tick();
    const timer = setInterval(tick, 2500);
    return () => { alive = false; clearInterval(timer); };
  }, [accepted, token]);

  useEffect(() => {
    const node = bodyRef.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [messages, pending, awaiting]);

  const accent = config?.accent || "#1677ff";
  const title = config?.title || "Чат";
  const letter = title.trim()[0]?.toUpperCase() || "E";

  async function accept() {
    setStarting(true);
    const t = await startSession(CHANNEL);
    setStarting(false);
    if (!t) return;
    localStorage.setItem(TOKEN_KEY, t);
    setToken(t);
    setAccepted(true);
  }

  async function send() {
    const text = input.trim();
    if (!text || !token || awaiting) return;
    setInput("");
    setPending((p) => [...p, text]);
    setAwaiting(true);
    await sendMessage(token, text).catch(() => undefined);
    try {
      ingestPoll(await poll(token, lastId.current));
    } catch {
      /* polling loop will retry */
    }
    setPending([]);
    setAwaiting(false);
  }

  const status = state === "operator"
    ? { label: "Отвечает специалист", dot: "#52c41a" }
    : state === "waiting"
      ? { label: "Передаём оператору", dot: "#faad14" }
      : { label: "Виртуальный помощник", dot: "#52c41a" };
  const unavailable = config !== null && !config.available;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", width: "100%", background: "#fff", fontFamily: "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif", color: "#1f1f1f", overflow: "hidden" }}>
      <div style={{ flex: "none", background: accent, padding: "14px 16px", display: "flex", alignItems: "center", gap: 11 }}>
        <div style={{ width: 36, height: 36, borderRadius: 10, background: "rgba(255,255,255,0.18)", display: "flex", alignItems: "center", justifyContent: "center", flex: "none", fontSize: 15, fontWeight: 700, color: "#fff" }}>{letter}</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 14.5, fontWeight: 600, color: "#fff", lineHeight: 1.2 }}>{title}</div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 2 }}>
            <span style={{ width: 7, height: 7, borderRadius: "50%", background: status.dot, flex: "none" }} />
            <span style={{ fontSize: 11.5, color: "rgba(255,255,255,0.92)" }}>{unavailable ? "Временно недоступен" : status.label}</span>
          </div>
        </div>
        <button onClick={closePanel} aria-label="Свернуть" style={{ width: 30, height: 30, borderRadius: 8, border: "none", background: "rgba(255,255,255,0.14)", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", flex: "none" }}>
          <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><line x1="5" y1="12" x2="19" y2="12" /></svg>
        </button>
      </div>

      <div ref={bodyRef} style={{ flex: 1, minHeight: 0, overflowY: "auto", background: "#f7f8fa", padding: "16px 14px" }}>
        {config === null && <div style={{ textAlign: "center", color: "#8c8c8c", padding: 24, fontSize: 13 }}>Загрузка…</div>}

        {unavailable && (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center", padding: "26px 14px" }}>
            <div style={{ width: 52, height: 52, borderRadius: "50%", background: "#fff7e6", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 14 }}>
              <svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="#d48806" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>
            </div>
            <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700 }}>Чат временно недоступен</h3>
            <p style={{ margin: "8px 0 0", fontSize: 13, color: "#595959", lineHeight: 1.5, maxWidth: 280 }}>Напишите нам в другом канале — ответим как можно скорее.</p>
          </div>
        )}

        {config?.available && !accepted && (
          <>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center", padding: "20px 12px 8px" }}>
              <div style={{ width: 56, height: 56, borderRadius: 16, background: "#e6f4ff", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 14 }}><span style={{ fontSize: 24, fontWeight: 700, color: accent }}>{letter}</span></div>
              <h3 style={{ margin: 0, fontSize: 17, fontWeight: 700 }}>{title}</h3>
              <p style={{ margin: "8px 0 0", fontSize: 13, color: "#595959", lineHeight: 1.5, maxWidth: 280 }}>{config.greeting}</p>
            </div>
            <div style={{ marginTop: 18, background: "#fff", border: "1px solid #f0f0f0", borderRadius: 12, padding: 14 }}>
              <div style={{ fontSize: 12, color: "#595959", lineHeight: 1.5 }}>{config.consent?.text} · ред. {config.consent?.version}</div>
            </div>
          </>
        )}

        {config?.available && accepted && (
          <>
            <div style={{ textAlign: "center", marginBottom: 14 }}><span style={{ display: "inline-block", padding: "3px 11px", borderRadius: 20, background: "#eef0f2", fontSize: 11, color: "#8c8c8c" }}>Сегодня</span></div>
            {config.greeting && <Bubble author="ai" text={config.greeting} accent={accent} />}
            {messages.map((m) => (m.author === "system"
              ? <div key={m.id} style={{ textAlign: "center", margin: "12px 0" }}><span style={{ display: "inline-block", padding: "4px 12px", borderRadius: 20, background: "#e6f4ff", border: "1px solid #91caff", fontSize: 11.5, color: "#0958d9" }}>{m.text}</span></div>
              : <Bubble key={m.id} author={m.author} text={m.text} accent={accent} />))}
            {pending.map((t, i) => <Bubble key={`p${i}`} author="client" text={t} accent={accent} pendingState />)}
            {awaiting && <Typing />}
          </>
        )}
      </div>

      {config?.available && !accepted && (
        <div style={{ flex: "none", background: "#fff", borderTop: "1px solid #f0f0f0", padding: "12px 14px 14px" }}>
          <button onClick={accept} disabled={starting} style={{ width: "100%", height: 44, borderRadius: 10, border: "none", background: accent, color: "#fff", fontSize: 14, fontWeight: 600, cursor: "pointer" }}>{starting ? "Запуск…" : "Принять и начать чат"}</button>
        </div>
      )}
      {config?.available && accepted && (
        <div style={{ flex: "none", background: "#fff", borderTop: "1px solid #f0f0f0", padding: "10px 12px 12px" }}>
          {state === "ai" && (config.quickReplies?.length ?? 0) > 0 && pending.length === 0 && messages.length === 0 && (
            <div style={{ display: "flex", gap: 7, flexWrap: "wrap", marginBottom: 9 }}>
              {config.quickReplies!.map((q) => (
                <button key={q} onClick={() => setInput(q)} style={{ padding: "6px 12px", borderRadius: 16, border: "1px solid #d6e4ff", background: "#f0f7ff", color: "#0958d9", fontSize: 12, fontWeight: 500, cursor: "pointer" }}>{q}</button>
              ))}
            </div>
          )}
          <div style={{ display: "flex", alignItems: "flex-end", gap: 8, border: "1px solid #e8e8e8", borderRadius: 12, padding: "6px 6px 6px 12px", background: "#fff" }}>
            <textarea
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void send(); } }}
              placeholder="Напишите сообщение…"
              style={{ flex: 1, border: "none", outline: "none", resize: "none", fontSize: 13.5, lineHeight: 1.5, color: "#262626", fontFamily: "inherit", padding: "6px 0", maxHeight: 90 }}
            />
            <button onClick={() => void send()} aria-label="Отправить" style={{ width: 34, height: 34, borderRadius: 8, border: "none", background: accent, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", flex: "none" }}>
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></svg>
            </button>
          </div>
        </div>
      )}
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
        {isOperator
          ? <span style={{ fontSize: 11, fontWeight: 600 }}>О</span>
          : <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="#8c8c8c" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="8" r="3.2" /><path d="M5.5 20a6.5 6.5 0 0 1 13 0" /></svg>}
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
        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="#8c8c8c" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="8" r="3.2" /><path d="M5.5 20a6.5 6.5 0 0 1 13 0" /></svg>
      </div>
      <div style={{ background: "#fff", border: "1px solid #eee", borderRadius: "14px 14px 14px 4px", padding: "12px 14px", display: "flex", alignItems: "center", gap: 5 }}>
        {[0, 0.2, 0.4].map((d) => <span key={d} style={{ width: 6, height: 6, borderRadius: "50%", background: "#b37feb", animation: `wcTyping 1.2s infinite ease-in-out ${d}s` }} />)}
      </div>
    </div>
  );
}

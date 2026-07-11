const { ActorBadge, Icon } = window.EdevsHubDesignSystem_e4c9df;

/* Recreation of design/baseline/ChatPanel.dc.html — Foxray's embedded web-chat
   widget. States: welcome (consent) / ai / operator handoff / checkout card / unavailable. */
function WebChatWidget() {
  const [state, setState] = React.useState("ai");
  const isWelcome = state === "welcome";
  const isAI = state === "ai";
  const isOperator = state === "operator";
  const isCheckout = state === "checkout";
  const isUnavailable = state === "unavailable";
  const isConversation = isAI || isOperator || isCheckout;

  const status = isOperator || isCheckout
    ? { label: "Отвечает специалист", dot: "#52c41a" }
    : isUnavailable
    ? { label: "Временно недоступен", dot: "#faad14" }
    : isWelcome
    ? { label: "Обычно отвечаем за пару минут", dot: "#52c41a" }
    : { label: "Оператор · на связи", dot: "#52c41a" };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", width: "100%", background: "#fff", fontFamily: "var(--font-sans)", color: "#1f1f1f", overflow: "hidden" }}>
      <div style={{ flex: "none", background: "var(--primary)", padding: "14px 16px", display: "flex", alignItems: "center", gap: 11 }}>
        <div style={{ width: 36, height: 36, borderRadius: 10, background: "rgba(255,255,255,0.18)", display: "flex", alignItems: "center", justifyContent: "center", flex: "none", fontSize: 15, fontWeight: 700, color: "#fff" }}>F</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 14.5, fontWeight: 600, color: "#fff", lineHeight: 1.2 }}>Foxray</div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 2 }}>
            <span style={{ width: 7, height: 7, borderRadius: "50%", background: status.dot, flex: "none" }}></span>
            <span style={{ fontSize: 11.5, color: "rgba(255,255,255,0.92)" }}>{status.label}</span>
          </div>
        </div>
        <select value={state} onChange={(e) => setState(e.target.value)} style={{ background: "rgba(255,255,255,0.14)", color: "#fff", border: "none", borderRadius: 8, fontSize: 11, padding: "5px 6px" }}>
          <option value="welcome">welcome</option>
          <option value="ai">ai</option>
          <option value="operator">operator</option>
          <option value="checkout">checkout</option>
          <option value="unavailable">unavailable</option>
        </select>
      </div>

      <div style={{ flex: 1, minHeight: 0, overflowY: "auto", background: "#f7f8fa", padding: "16px 14px" }}>
        {isWelcome && (
          <>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center", padding: "20px 12px 8px" }}>
              <div style={{ width: 56, height: 56, borderRadius: 16, background: "var(--primary-bg)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 14 }}>
                <span style={{ fontSize: 24, fontWeight: 700, color: "var(--primary)" }}>F</span>
              </div>
              <h3 style={{ margin: 0, fontSize: 17, fontWeight: 700 }}>Чат Foxray</h3>
              <p style={{ margin: "8px 0 0", fontSize: 13, color: "#595959", lineHeight: 1.5, maxWidth: 280 }}>Здравствуйте! Помогу подобрать тариф и ответить на вопросы по Foxray. Чем можем помочь?</p>
            </div>
            <div style={{ marginTop: 18, background: "#fff", border: "1px solid #f0f0f0", borderRadius: 12, padding: 14 }}>
              <div style={{ fontSize: 12, color: "#595959", lineHeight: 1.5 }}>Продолжая, вы соглашаетесь на обработку сообщений для ответа на обращение. <a href="#" style={{ color: "var(--primary)" }}>Политика обработки данных</a> · ред. v3.</div>
            </div>
          </>
        )}

        {isUnavailable && (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center", padding: "26px 14px" }}>
            <div style={{ width: 52, height: 52, borderRadius: "50%", background: "var(--warning-bg-strong)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 14 }}>
              <Icon name="alertTriangle" size={26} color="var(--warning-text)" />
            </div>
            <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700 }}>Чат временно недоступен</h3>
            <p style={{ margin: "8px 0 0", fontSize: 13, color: "#595959", lineHeight: 1.5, maxWidth: 280 }}>Мы не можем принять сообщение прямо сейчас. Напишите нам в другом канале.</p>
            <div style={{ display: "flex", flexDirection: "column", gap: 9, width: "100%", maxWidth: 280, marginTop: 18 }}>
              <a href="#" style={{ display: "flex", alignItems: "center", gap: 10, padding: "11px 13px", border: "1px solid #efdbff", background: "#fff", borderRadius: 10, textDecoration: "none" }}>
                <span style={{ width: 26, height: 26, borderRadius: 7, background: "#f2f0ff", display: "flex", alignItems: "center", justifyContent: "center", flex: "none" }}><span style={{ width: 9, height: 9, borderRadius: "50%", background: "#6b5be0" }}></span></span>
                <span style={{ fontSize: 13, fontWeight: 500, color: "#262626", flex: 1, textAlign: "left" }}>Написать в MAX</span>
              </a>
              <a href="#" style={{ display: "flex", alignItems: "center", gap: 10, padding: "11px 13px", border: "1px solid #d6ebfa", background: "#fff", borderRadius: 10, textDecoration: "none" }}>
                <span style={{ width: 26, height: 26, borderRadius: 7, background: "#eaf6fd", display: "flex", alignItems: "center", justifyContent: "center", flex: "none" }}><span style={{ width: 9, height: 9, borderRadius: "50%", background: "#2f8fd0" }}></span></span>
                <span style={{ fontSize: 13, fontWeight: 500, color: "#262626", flex: 1, textAlign: "left" }}>Написать в Telegram</span>
              </a>
            </div>
          </div>
        )}

        {isConversation && (
          <>
            <div style={{ textAlign: "center", marginBottom: 14 }}><span style={{ display: "inline-block", padding: "3px 11px", borderRadius: 20, background: "#eef0f2", fontSize: 11, color: "#8c8c8c" }}>Сегодня</span></div>
            <Bubble mine text="Здравствуйте! Чем Max отличается от Pro?" time="14:01 · доставлено" />
            <AgentBubble actor="ai" text="Pro — для одного пользователя (₽4 900/мес), Max — командный с расширенными лимитами и приоритетной поддержкой (₽9 900/мес)." meta="Оператор · 14:01" />
            <Bubble mine text="Нас 6 человек, берём Max на год." time="14:02 · доставлено" />
            {isOperator && (
              <>
                <div style={{ textAlign: "center", margin: "14px 0 12px" }}>
                  <span style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "5px 13px", borderRadius: 20, background: "var(--primary-bg)", border: "1px solid var(--primary-border)", fontSize: 11.5, color: "#0958d9", fontWeight: 500 }}>Подключился специалист · история уже у него</span>
                </div>
                <AgentBubble actor="human" initials="АК" text="Здравствуйте! Анна, Foxray. Помогу с оформлением Max на 6 мест." meta="Анна · специалист · 14:03" />
              </>
            )}
            {isAI && (
              <div style={{ display: "flex", gap: 8, marginBottom: 4 }}>
                <ActorBadge actor="ai" />
                <div style={{ background: "#fff", border: "1px solid #eee", borderRadius: "14px 14px 14px 4px", padding: "12px 14px", display: "flex", alignItems: "center", gap: 5 }}>
                  <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--ai-lighter)", animation: "hub-typing 1.2s infinite ease-in-out" }}></span>
                  <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--ai-lighter)", animation: "hub-typing 1.2s infinite ease-in-out .2s" }}></span>
                  <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--ai-lighter)", animation: "hub-typing 1.2s infinite ease-in-out .4s" }}></span>
                </div>
              </div>
            )}
            {isCheckout && (
              <div style={{ display: "flex", gap: 8, marginBottom: 6 }}>
                <ActorBadge actor="human" initials="АК" color="var(--primary)" />
                <div style={{ maxWidth: "84%", width: "100%" }}>
                  <div style={{ background: "#fff", border: "1px solid #e8e8e8", borderRadius: 14, overflow: "hidden", boxShadow: "var(--shadow-sm)" }}>
                    <div style={{ padding: "13px 15px 11px", borderBottom: "1px solid #f5f5f5" }}>
                      <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.04em", color: "var(--ai)", marginBottom: 6 }}>ОФОРМЛЕНИЕ ПОКУПКИ</div>
                      <div style={{ fontSize: 15, fontWeight: 700 }}>Foxray Max · 6 мест</div>
                      <div style={{ display: "flex", alignItems: "baseline", gap: 7, marginTop: 7 }}>
                        <span style={{ fontSize: 21, fontWeight: 700 }}>₽95 040</span><span style={{ fontSize: 12, color: "#8c8c8c" }}>/ год · −20%</span>
                      </div>
                    </div>
                    <div style={{ padding: "11px 15px 13px" }}>
                      <a href="#" style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 7, height: 40, borderRadius: 9, background: "var(--primary)", color: "#fff", fontSize: 13.5, fontWeight: 600, textDecoration: "none" }}>Перейти к покупке<Icon name="arrowRight" size={15} /></a>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {isConversation && (
        <div style={{ flex: "none", background: "#fff", borderTop: "1px solid #f0f0f0", padding: "10px 12px 12px" }}>
          {isAI && (
            <div style={{ display: "flex", gap: 7, flexWrap: "wrap", marginBottom: 9 }}>
              <QuickReply>Сравнить тарифы</QuickReply>
              <QuickReply>Есть ли пробный период?</QuickReply>
            </div>
          )}
          <div style={{ display: "flex", alignItems: "flex-end", gap: 8, border: "1px solid #e8e8e8", borderRadius: 12, padding: "6px 6px 6px 12px" }}>
            <textarea rows={1} placeholder="Напишите сообщение…" style={{ flex: 1, border: "none", outline: "none", resize: "none", fontSize: 13.5, lineHeight: 1.5, color: "#262626", fontFamily: "inherit", padding: "6px 0" }} />
            <button style={{ width: 34, height: 34, borderRadius: 8, border: "none", background: "var(--primary)", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", flex: "none" }}>
              <svg viewBox="0 0 24 24" width={16} height={16} fill="none" stroke="#fff" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></svg>
            </button>
          </div>
        </div>
      )}
      {isWelcome && (
        <div style={{ flex: "none", background: "#fff", borderTop: "1px solid #f0f0f0", padding: "12px 14px 14px" }}>
          <button onClick={() => setState("ai")} style={{ width: "100%", height: 44, borderRadius: 10, border: "none", background: "var(--primary)", color: "#fff", fontSize: 14, fontWeight: 600, cursor: "pointer" }}>Принять и начать чат</button>
        </div>
      )}
      {isUnavailable && (
        <div style={{ flex: "none", background: "#fafafa", borderTop: "1px solid #f0f0f0", padding: "12px 14px", display: "flex", alignItems: "center", gap: 9, justifyContent: "center" }}>
          <span style={{ fontSize: 12, color: "#8c8c8c" }}>Отправка сообщений недоступна</span>
        </div>
      )}
    </div>
  );
}

function Bubble({ text, time }) {
  return (
    <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 10 }}>
      <div style={{ maxWidth: "78%" }}>
        <div style={{ background: "var(--primary)", color: "#fff", borderRadius: "14px 14px 4px 14px", padding: "9px 13px", fontSize: 13.5, lineHeight: 1.45 }}>{text}</div>
        <div style={{ fontSize: 10.5, color: "#bfbfbf", margin: "3px 4px 0 0", textAlign: "right" }}>{time}</div>
      </div>
    </div>
  );
}

function AgentBubble({ actor, initials, text, meta }) {
  return (
    <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
      <ActorBadge actor={actor} initials={initials} color="var(--primary)" />
      <div style={{ maxWidth: "78%" }}>
        <div style={{ background: "#fff", border: "1px solid #eee", borderRadius: "14px 14px 14px 4px", padding: "9px 13px", fontSize: 13.5, lineHeight: 1.45, color: "#262626" }}>{text}</div>
        <div style={{ fontSize: 10.5, color: "#bfbfbf", margin: "3px 0 0 4px" }}>{meta}</div>
      </div>
    </div>
  );
}

function QuickReply({ children }) {
  return <button style={{ padding: "6px 12px", borderRadius: 16, border: "1px solid var(--primary-border)", background: "#f0f7ff", color: "#0958d9", fontSize: 12, fontWeight: 500, cursor: "pointer" }}>{children}</button>;
}

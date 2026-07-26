import { useState } from "react";

import { Icon } from "../../shared/icons";
import { sendOperatorMessage } from "./model";
import type { ControlMode } from "./types";

export function Composer({ mode, loaded, assignedOperatorName, conversationId, onClaim, onRelease, onReturnQueue, onClose, onSent }: { mode: ControlMode; loaded: boolean; assignedOperatorName?: string; conversationId: number | null; onClaim: () => void; onRelease: () => void; onReturnQueue: () => void; onClose: () => void; onSent: () => void }) {
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState("");

  if (conversationId == null) {
    return <div className="sales-composer"><div className="sales-waiting-composer"><div><strong>Выберите диалог</strong></div></div></div>;
  }

  if (!loaded) {
    return <div className="sales-composer"><div className="sales-waiting-composer"><div><strong>Загрузка диалога…</strong></div></div></div>;
  }

  if (mode === "closed") {
    return (
      <div className="sales-composer"><div className="sales-waiting-composer">
        <span><Icon name="lock" size={19} /></span>
        <div><strong>Диалог закрыт</strong><p>История сохранена. Новое обращение клиента создаст новый диалог.</p></div>
      </div></div>
    );
  }

  if (mode === "assigned") {
    return (
      <div className="sales-composer"><div className="sales-waiting-composer">
        <span><Icon name="lock" size={19} /></span>
        <div><strong>{assignedOperatorName ? `Диалог ведёт ${assignedOperatorName}` : "Диалог ведёт другой оператор"}</strong><p>Отправка сообщений доступна назначенному оператору.</p></div>
      </div></div>
    );
  }

  if (mode === "waiting") {
    return (
      <div className="sales-composer"><div className="sales-waiting-composer">
        <span><Icon name="lock" size={19} /></span>
        <div><strong>Диалог ждёт оператора</strong><p>Возьмите диалог, чтобы ответить клиенту. AI поставлен на паузу.</p></div>
        <button className="sales-claim-button" onClick={onClaim}><Icon name="check" size={15} />Забрать диалог</button>
      </div></div>
    );
  }

  if (mode === "ai") {
    return (
      <div className="sales-composer"><div className="sales-ai-composer">
        <span><Icon name="robot" size={19} /></span>
        <div><strong>AI ведёт диалог</strong><p>Перехватите, чтобы ответить вручную. Контроль перейдёт к вам.</p></div>
        <button className="sales-ai-button" onClick={onClaim}>Перехватить AI</button>
      </div></div>
    );
  }

  async function send() {
    const value = text.trim();
    if (!value || conversationId == null || sending) return;
    setSending(true);
    setSendError("");
    try {
      await sendOperatorMessage(conversationId, value);
      setText("");
      onSent();
    } catch (error) {
      setSendError(error instanceof Error ? error.message : "Не удалось отправить сообщение");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="sales-composer">
      <div className="sales-human-tools">
        <button onClick={onReturnQueue}>Вернуть в очередь</button>
        <span />
        <button className="ai" onClick={onRelease}>Вернуть AI</button>
        <button onClick={onClose}>Закрыть</button>
      </div>
      <div className="sales-message-input">
        <textarea
          rows={1}
          placeholder="Введите сообщение…"
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void send(); } }}
        />
        <button onClick={() => void send()} disabled={sending}>Отправить<Icon name="send" size={15} /></button>
      </div>
      {sendError && <div className="sales-composer-error">{sendError}</div>}
    </div>
  );
}

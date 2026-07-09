import { useState } from "react";

import { Icon } from "../../shared/icons";
import { sendOperatorMessage } from "./model";
import type { ControlMode } from "./types";

export function Composer({ mode, conversationId, onClaim, onRelease, onReturnQueue, onClose, onSent }: { mode: ControlMode; conversationId: number | null; onClaim: () => void; onRelease: () => void; onReturnQueue: () => void; onClose: () => void; onSent: () => void }) {
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);

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
    try {
      await sendOperatorMessage(conversationId, value);
      setText("");
      onSent();
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
        <button aria-label="Прикрепить файл"><Icon name="paperclip" size={19} /></button>
        <textarea
          rows={1}
          placeholder="Введите сообщение…"
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void send(); } }}
        />
        <button onClick={() => void send()} disabled={sending}>Отправить<Icon name="send" size={15} /></button>
      </div>
    </div>
  );
}

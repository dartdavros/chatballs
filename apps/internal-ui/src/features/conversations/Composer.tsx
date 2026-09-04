import { useEffect, useMemo, useRef, useState } from "react";

import { Icon } from "../../shared/icons";
import { fetchReplyTemplates, sendOperatorMessage, sendVoiceMessage, type ReplyTemplateRef } from "./model";
import { formatDuration } from "./VoiceMessage";
import { useVoiceRecorder } from "./useVoiceRecorder";
import type { ChannelKey, ControlMode } from "./types";

export function Composer({ mode, loaded, assignedOperatorName, conversationId, channel, onClaim, onRelease, onReturnQueue, onClose, onSent }: { mode: ControlMode; loaded: boolean; assignedOperatorName?: string; conversationId: number | null; channel?: ChannelKey; onClaim: () => void; onRelease: () => void; onReturnQueue: () => void; onClose: () => void; onSent: () => void }) {
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState("");
  const [templates, setTemplates] = useState<ReplyTemplateRef[]>([]);
  const [templatesOpen, setTemplatesOpen] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    fetchReplyTemplates().then(setTemplates).catch(() => setTemplates([]));
  }, []);

  // Шаблоны «/» (дизайн-базлайн v2 §9): ввод «/» в начале открывает список,
  // продолжение ввода фильтрует по названию.
  const slashQuery = text.startsWith("/") ? text.slice(1).trim().toLowerCase() : null;
  const visibleTemplates = useMemo(() => {
    if (templates.length === 0) return [];
    if (slashQuery === null) return templates;
    return templates.filter((template) => template.title.toLowerCase().includes(slashQuery));
  }, [templates, slashQuery]);
  const menuOpen = templatesOpen || (slashQuery !== null && visibleTemplates.length > 0);

  function applyTemplate(template: ReplyTemplateRef) {
    setText(template.text);
    setTemplatesOpen(false);
    textareaRef.current?.focus();
  }

  // Запись голосового: поддержана в Telegram-диалогах (отправка sendVoice).
  const recorder = useVoiceRecorder({
    onSend: async (audio, duration) => {
      if (conversationId == null) return;
      await sendVoiceMessage(conversationId, audio, duration);
      onSent();
    },
  });
  // Каналы с транспортом отправки голосовых (transports.supports_voice_send).
  const voiceAvailable = recorder.supported && (channel === "TG" || channel === "MAX" || channel === "WEB");

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

  if (recorder.state !== "idle") {
    return (
      <div className="sales-composer">
        <div className="voice-recorder">
          <button aria-label="Отменить запись" className="voice-recorder-cancel" title="Отменить запись" type="button" onClick={recorder.cancel}>
            <Icon name="trash" size={16} />
          </button>
          <span className="voice-recorder-timer"><i />{formatDuration(recorder.seconds)}</span>
          <span className="voice-recorder-hint">
            {recorder.state === "sending" ? "Отправка…" : "Идёт запись. Esc — отменить, Enter — отправить"}
          </span>
          <button className="voice-recorder-send" disabled={recorder.state === "sending"} type="button" onClick={recorder.stopAndSend}>
            <Icon name="send" size={14} />Отправить
          </button>
        </div>
        {recorder.errorText && <div className="sales-composer-error">{recorder.errorText}</div>}
      </div>
    );
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
        {menuOpen && (
          <div className="composer-templates-menu">
            {visibleTemplates.length === 0 && <p>Нет подходящих шаблонов</p>}
            {visibleTemplates.map((template) => (
              <button key={template.id} type="button" onMouseDown={(event) => { event.preventDefault(); applyTemplate(template); }}>
                <strong>{template.title}</strong>
                <small>{template.text.replace(/\s+/g, " ").slice(0, 80)}</small>
              </button>
            ))}
          </div>
        )}
        {templates.length > 0 && (
          <button
            className="composer-templates-button"
            title="Шаблоны ответов · /"
            type="button"
            onClick={() => setTemplatesOpen((open) => !open)}
          >
            <Icon name="list" size={16} />
          </button>
        )}
        {voiceAvailable && (
          <button
            className="composer-templates-button"
            title="Записать голосовое"
            type="button"
            onClick={() => void recorder.start()}
          >
            <Icon name="message" size={16} />
          </button>
        )}
        <textarea
          ref={textareaRef}
          rows={1}
          placeholder={templates.length > 0 ? "Введите сообщение… («/» — шаблоны)" : "Введите сообщение…"}
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Escape" && menuOpen) { setTemplatesOpen(false); if (slashQuery !== null) setText(""); return; }
            if (event.key === "Enter" && !event.shiftKey) {
              if (slashQuery !== null && visibleTemplates.length > 0) { event.preventDefault(); applyTemplate(visibleTemplates[0]); return; }
              event.preventDefault();
              void send();
            }
          }}
          onBlur={() => setTemplatesOpen(false)}
        />
        <button onClick={() => void send()} disabled={sending}>Отправить<Icon name="send" size={15} /></button>
      </div>
      {sendError && <div className="sales-composer-error">{sendError}</div>}
    </div>
  );
}

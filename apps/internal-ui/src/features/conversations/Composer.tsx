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
    return <div className="sales-composer"><div className="composer-locked"><div><strong>Выберите диалог</strong></div></div></div>;
  }

  if (!loaded) {
    return <div className="sales-composer"><div className="composer-locked"><div><strong>Загрузка диалога…</strong></div></div></div>;
  }

  // Кадр E: закрытый диалог — композер заменён сообщением о закрытии.
  if (mode === "closed") {
    return (
      <div className="sales-composer"><div className="composer-locked">
        <span><Icon name="lock" size={19} /></span>
        <div><strong>Диалог закрыт</strong><p>История сохранена. Новое обращение клиента создаст новый диалог.</p></div>
      </div></div>
    );
  }

  // Кадр D: ведёт другой сотрудник — композер заблокирован, взять можно явно.
  if (mode === "assigned") {
    return (
      <div className="sales-composer"><div className="composer-locked">
        <span><Icon name="lock" size={19} /></span>
        <div><strong>{assignedOperatorName ? `Диалог ведёт ${assignedOperatorName}` : "Диалог ведёт другого сотрудника"}</strong><p>Отвечать может ответственный. Возьмите диалог, чтобы продолжить самостоятельно.</p></div>
        <button className="composer-locked-action" type="button" onClick={onClaim}>Взять диалог</button>
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

  // Кадры A–C: композер активен всегда (решение 2) — первое сообщение
  // перехватывает диалог; над полем одна строка-предупреждение.
  const warning = mode === "ai"
    ? { color: "var(--ai)", text: "AI ведёт диалог. Ваше сообщение перехватит его — AI перестанет отвечать" }
    : mode === "waiting"
      ? { color: "var(--warning-text)", dot: "var(--warning)", text: "Клиент ждёт. Ваше сообщение возьмёт диалог на вас" }
      : null;

  return (
    <div className="sales-composer">
      <div className="composer-wrap">
        {warning && <div className="composer-warning" style={{ color: warning.color }}><i style={{ background: warning.dot ?? warning.color }} />{warning.text}</div>}
        <div className="composer-box">
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
          <textarea
            ref={textareaRef}
            rows={1}
            placeholder="Введите сообщение… Shift+Enter — перенос строки, «/» — шаблон ответа"
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
          <div className="composer-toolbar">
            {voiceAvailable && (
              <button className="composer-tool" title="Записать голосовое" aria-label="Записать голосовое" type="button" onClick={() => void recorder.start()}>
                <Icon name="mic" size={17} />
              </button>
            )}
            {templates.length > 0 && (
              <button className="composer-tool is-labeled" title="Шаблоны ответов · /" type="button" onClick={() => setTemplatesOpen((open) => !open)}>
                <Icon name="text" size={16} />Шаблоны
              </button>
            )}
            <span className="composer-spacer" />
            <button className="composer-send" type="button" onClick={() => void send()} disabled={sending}>Отправить<kbd>⏎</kbd></button>
          </div>
        </div>
      </div>
      {sendError && <div className="sales-composer-error">{sendError}</div>}
    </div>
  );
}

import { useEffect, useMemo, useRef, useState } from "react";

import { Icon, LogoSpinner } from "../../shared/icons";
import { EmojiPicker } from "./EmojiPicker";
import { useMediaQuery } from "../../shared/useMediaQuery";
import { fetchReplyTemplates, sendFileMessage, sendOperatorMessage, sendVoiceMessage, type ReplyTemplateRef } from "./model";
import { formatSize } from "../ai/knowledge/model";
import { formatDuration } from "./VoiceMessage";
import { useVoiceRecorder } from "./useVoiceRecorder";
import type { ChannelKey, ControlMode } from "./types";

const MAX_FILE_BYTES = 20 * 1024 * 1024;

export function Composer({ mode, loaded, assignedOperatorName, conversationId, channel, voiceAllowed = true, onClaim, onRelease, onReturnQueue, onClose, onSent }: { mode: ControlMode; loaded: boolean; assignedOperatorName?: string; conversationId: number | null; channel?: ChannelKey; voiceAllowed?: boolean; onClaim: () => void; onRelease: () => void; onReturnQueue: () => void; onClose: () => void; onSent: () => void }) {
  const [text, setText] = useState("");
  const compact = useMediaQuery("(max-width: 768px)");
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState("");
  const [templates, setTemplates] = useState<ReplyTemplateRef[]>([]);
  const [templatesOpen, setTemplatesOpen] = useState(false);
  const [attachment, setAttachment] = useState<File | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Поле растёт под текст, как в мессенджере: до 7 строк, дальше скролл.
  // Композер прижат к низу ленты, поэтому рост идёт вверх.
  useEffect(() => {
    const node = textareaRef.current;
    if (!node) return;
    node.style.height = "auto";
    node.style.height = node.scrollHeight > 0 ? `${node.scrollHeight}px` : "";
  }, [text, attachment]);

  // Сброс черновика вложения при смене диалога.
  useEffect(() => { setAttachment(null); setSendError(""); }, [conversationId]);

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

  // Запись голосового: во всех каналах (TG/MAX sendVoice, почта — вложением, Web — поллингом).
  const recorder = useVoiceRecorder({
    onSend: async (audio, duration) => {
      if (conversationId == null) return;
      await sendVoiceMessage(conversationId, audio, duration);
      onSent();
    },
  });
  // Микрофон — если браузер умеет запись и голосовые разрешены в точке входа.
  const voiceAvailable = recorder.supported && voiceAllowed;

  if (conversationId == null) {
    return <div className="sales-composer"><div className="composer-locked"><div><strong>Выберите диалог</strong></div></div></div>;
  }

  if (!loaded) {
    return <div className="sales-composer"><div className="composer-locked is-loading"><LogoSpinner size={22} /></div></div>;
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

  // Вставка эмодзи в позицию курсора; фокус возвращается в поле.
  function insertEmoji(emoji: string) {
    const area = textareaRef.current;
    const start = area?.selectionStart ?? text.length;
    const end = area?.selectionEnd ?? text.length;
    const next = text.slice(0, start) + emoji + text.slice(end);
    setText(next);
    window.requestAnimationFrame(() => {
      if (!area) return;
      area.focus();
      area.setSelectionRange(start + emoji.length, start + emoji.length);
    });
  }

  async function send() {
    const value = text.trim();
    if ((!value && !attachment) || conversationId == null || sending) return;
    setSending(true);
    setSendError("");
    try {
      if (attachment) {
        // Файл уходит с подписью — текст поля становится подписью к файлу.
        await sendFileMessage(conversationId, attachment, value);
        setAttachment(null);
      } else {
        await sendOperatorMessage(conversationId, value);
      }
      setText("");
      onSent();
    } catch (error) {
      setSendError(error instanceof Error ? error.message : "Не удалось отправить сообщение");
    } finally {
      setSending(false);
    }
  }

  function pickFile(file: File | null) {
    if (!file) return;
    if (file.size > MAX_FILE_BYTES) {
      setSendError("Файл больше 20 МБ");
      return;
    }
    setSendError("");
    setAttachment(file);
    textareaRef.current?.focus();
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
          {attachment && (
            <div className="composer-attachment">
              <Icon name="paperclip" size={14} />
              <strong title={attachment.name}>{attachment.name}</strong>
              <small>{formatSize(attachment.size)}</small>
              <button aria-label="Убрать файл" title="Убрать файл" type="button" disabled={sending} onClick={() => { setAttachment(null); if (fileInputRef.current) fileInputRef.current.value = ""; }}>
                <Icon name="xCircle" size={15} />
              </button>
            </div>
          )}
          <textarea
            ref={textareaRef}
            rows={1}
            placeholder={attachment ? "Подпись к файлу (необязательно)…" : compact ? "Сообщение…" : "Введите сообщение… Shift+Enter — перенос строки, «/» — шаблон ответа"}
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
            onPaste={(event) => {
              const file = Array.from(event.clipboardData?.files ?? [])[0];
              if (file) { event.preventDefault(); pickFile(file); }
            }}
          />
          <div className="composer-toolbar">
            <EmojiPicker onPick={insertEmoji} disabled={sending} />
            <button className="composer-tool" title="Прикрепить" aria-label="Прикрепить файл" type="button" disabled={sending} onClick={() => fileInputRef.current?.click()}>
              <Icon name="paperclip" size={17} />
            </button>
            <input ref={fileInputRef} type="file" hidden onChange={(event) => { pickFile(event.target.files?.[0] ?? null); event.target.value = ""; }} />
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
            <button className="composer-send" type="button" onClick={() => void send()} disabled={sending || (!text.trim() && !attachment)}><span>Отправить</span><kbd>⏎</kbd><Icon name="send" size={17} /></button>
          </div>
        </div>
      </div>
      {sendError && <div className="sales-composer-error">{sendError}</div>}
    </div>
  );
}

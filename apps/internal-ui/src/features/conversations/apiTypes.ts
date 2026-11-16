import type { MessagePresentation, SiteField } from "@chatballs/contracts";

// kind: "" — текст, "contact_request" — запрос контакта, "contact" — клиент поделился номером.
export type ApiMessage = MessagePresentation & {
  externalDelivery?: { state: "queued" | "transport_accepted" | "unknown" | "failed" | "suppressed"; textFallback: boolean; initiative: boolean };
  externalVoice?: "ready";
  externalReturned?: boolean;
  templateUpdatedAt?: string;
  id: number;
  author: "CONTACT" | "AI" | "OPERATOR" | "SYSTEM";
  authorUserId?: number | null;
  authorName?: string;
  authorAvatarUrl?: string | null;
  kind?: string;
  text: string;
  // Код системного события: строку сервер уже собрал на языке читателя, код
  // остаётся интерфейсу для тона строки.
  systemEvent?: string;
  transferId?: number;
  // Вызов инструмента агентом (systemEvent="tool_called"): по turnId вызовы
  // одного хода собираются вместе; error — текст ошибки на языке читателя.
  toolCall?: {
    tool: string;
    ok: boolean;
    errorCode: string;
    error: string;
    durationMs: number;
    turnId: number | null;
  };
  contentHtml?: string;
  transport?: { provider: "EMAIL"; connectionId: number; threadId: number; direction: "INBOUND" | "OUTBOUND";
    senderAddress: string | null; recipientAddress: string | null; subject: string | null; mailboxName: string | null };
  createdAt: string;
  // Голосовое (kind="voice", дизайн-базлайн v2 кадр H).
  audioUrl?: string | null;
  durationSeconds?: number;
  transcript?: string;
  transcriptStatus?: "NONE" | "READY" | "FAILED";
  // Файл или фото (kind="file"): text — подпись.
  attachmentUrl?: string | null;
  attachmentName?: string;
  attachmentContentType?: string;
  attachmentSize?: number;
};

export const isImageAttachment = (message: Pick<ApiMessage, "attachmentContentType">) =>
  /^image\/(jpeg|png|gif|webp)$/.test(message.attachmentContentType ?? "");

export type HistoryItem = {
  id: number;
  channelName: string;
  provider: "EMAIL" | "MAX" | "TELEGRAM" | "VK" | "WEB" | null;
  lifecycle: "OPEN" | "CLOSED" | "SPAM";
  createdAt: string;
  lastActivityAt: string;
  topic?: string;
  handledBy?: string | null;
  preview: string;
};

export type ConversationPriority = "HIGH" | "MEDIUM" | "LOW" | "NONE";

export type ConversationLabelRef = { id: number; name: string; color: string };

export type ConversationCounters = {
  all: number;
  waiting: number;
  /** Ничей: взять может любой. */
  queue: number;
  /** Назначен лично на меня и ждёт, пока я возьму. */
  waitingOnMe: number;
  mine: number;
  /** Сколько минут держится личная очередь, прежде чем диалог вернётся всем. */
  assignmentTimeoutMinutes?: number;
  ungrouped: number;
  groups: Array<{ id: number; name: string; color?: string; count: number }>;
  agents: Array<{ id: number; code: string; name: string; count: number }>;
  assignees: Array<{ id: number; name: string; count: number; avatarUrl?: string | null }>;
};

export type ReplyTemplateRef = {
  id: number; title: string; text: string; updatedAt: string;
  scope: "PERSONAL" | "SHARED"; ownerId: number | null; categoryId: number | null; tagIds: number[];
};

export type ApiConversation = {
  externalExecution?: { waiting: "ordinary" | "long" | null; notices: ExternalNotice[] };
  access?: { actions: string[]; supervised: boolean; isParticipant: boolean; canReply: boolean; canControl: boolean };
  id: number;
  channel: { id: number; code: string; name: string };
  // voiceMessages/audioCalls/videoCalls — что разрешено в точке входа («Настройки → Голосовые и звонки»).
  connection: { id: number; provider: "EMAIL" | "MAX" | "TELEGRAM" | "VK" | "WEB"; name: string; voiceMessages?: boolean; audioCalls?: boolean; videoCalls?: boolean } | null;
  // Контакт — единственный источник identity диалога.
  // phone появляется после явного шаринга контакта; username (@логин TG/MAX) — только в detail-режиме.
  // isGuest — только в detail-режиме: имя гостя виджета — подпись «Гость · код», а не имя.
  siteFields?: SiteField[];
  contact: { id: number; name: string; email?: string; phone?: string; username?: string; avatarUrl?: string; description?: string; company?: string; city?: string; isGuest?: boolean } | null;
  lifecycle: "OPEN" | "CLOSED" | "SPAM";
  controlMode: "AI" | "HUMAN" | "PAUSED";
  expectedResponder: string;
  assignedOperatorId: number | null;
  assignmentVersion: number;
  assignedOperator: { id: number; name: string; avatarUrl?: string | null } | null;
  isAssignedToViewer: boolean;
  isParticipant?: boolean;
  /** С какого момента диалог ждёт человека (макет Q3/Q4). */
  waitingSince?: string | null;
  /** Когда назначили: от него считается срок личной очереди. */
  assignedAt?: string | null;
  group: { id: number; name: string; color?: string } | null;
  // Дизайн-базлайн v2: приоритет, метки, заметка, архив.
  priority: ConversationPriority;
  labels: ConversationLabelRef[];
  note: string;
  archivedAt: string | null;
  lastActivityAt: string;
  createdAt: string;
  lastMessage: ApiMessage | null;
  pendingCount?: number;
  // Сообщений в карточке нет: история — отдельная лента с окном (fetchMessages).
  history?: HistoryItem[];
  // Запрос контакта мог уйти вне загруженного окна истории — факт считает сервер.
  contactRequested?: boolean;
  // Только в карточке: включена ли у агента канала помощь оператору с черновиком.
  replyAssistanceEnabled?: boolean;
  canReleaseToAi?: boolean;
  hasAgent?: boolean;
};

export type ExternalNotice = { id: string; kind: "handoff" | "unavailable" | "timeout" | "voiceFailure" | "suppressed" | "unknown" | "partial"; summary: string; createdAt: string };

// Живые ленты (инбокс, история диалога) приходят окном: записи, признак
// продолжения и курсор на следующее окно.
export type WindowPage<T> = { items: T[]; hasMore: boolean; cursor: number | null };

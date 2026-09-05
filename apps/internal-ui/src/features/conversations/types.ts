// Общие типы workspace диалогов (sales + support). SPEC-HUB-0010 §8.2:
// общий conversation workspace, не отдельная реализация под каждый отдел.

export type DialogMode = "ai" | "closed" | "operator" | "wait";
export type ControlMode = "ai" | "assigned" | "closed" | "human" | "waiting";
export type ListTab = "all" | "mine" | "wait";
export type ChannelKey = "EMAIL" | "MAX" | "TG" | "WEB";

// Элемент списка диалогов (бывш. SalesDialog). Полностью generic.
export type ConversationListItem = {
  id: number;
  name: string;
  initials: string;
  avatarBg: string;
  avatarUrl?: string;
  product: string;
  channel: ChannelKey;
  email: string;
  mode: DialogMode;
  preview: string;
  time: string;
  unread: number;
  // Дизайн-базлайн v2: вкладка «Мои», приоритет и бейджи строки.
  isMine: boolean;
  priority: "HIGH" | "MEDIUM" | "LOW" | "NONE";
  labels: Array<{ id: number; name: string; color: string }>;
  // Строка диалога (решение 4): агент в цвете, группа с точкой, таймер ожидания,
  // «↩» — последнее сообщение наше.
  agentName: string;
  agentColor: string;
  groupName: string | null;
  groupColor: string;
  waitLabel: string | null;
  lastIsOurs: boolean;
};

export type StatusInfo = {
  label: string;
  color: string;
  bg: string;
  border: string;
  dot: string;
};

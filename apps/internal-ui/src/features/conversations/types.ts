// Общие типы workspace диалогов (sales + support). SPEC-HUB-0010 §8.2:
// общий conversation workspace, не отдельная реализация под каждый отдел.

export type DialogMode = "ai" | "closed" | "operator" | "wait";
export type ControlMode = "ai" | "assigned" | "closed" | "human" | "waiting";
export type ListTab = "ai" | "all" | "operator" | "unread" | "wait";
export type ChannelKey = "EMAIL" | "MAX" | "TG" | "WEB";

// Элемент списка диалогов (бывш. SalesDialog). Полностью generic.
export type ConversationListItem = {
  id: number;
  name: string;
  initials: string;
  avatarBg: string;
  product: string;
  channel: ChannelKey;
  email: string;
  mode: DialogMode;
  preview: string;
  time: string;
  unread: number;
};

export type StatusInfo = {
  label: string;
  color: string;
  bg: string;
  border: string;
  dot: string;
};

export type DialogMode = "ai" | "closed" | "operator" | "wait";
export type ControlMode = "ai" | "human" | "waiting";
export type ListTab = "ai" | "all" | "operator" | "unread" | "wait";
export type RightTab = "client" | "history" | "product";
export type ChannelKey = "MAX" | "TG" | "WEB";

export type SalesDialog = {
  id: number;
  name: string;
  initials: string;
  avatarBg: string;
  product: string;
  channel: ChannelKey;
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

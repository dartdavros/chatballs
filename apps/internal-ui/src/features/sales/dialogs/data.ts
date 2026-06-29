import type { ChannelKey, ControlMode, DialogMode, SalesDialog, StatusInfo } from "./types";

export const dialogs: SalesDialog[] = [
  { id: 1, name: "Мария Соколова", initials: "МС", avatarBg: "#eb6f4b", product: "FirePage", channel: "MAX", mode: "wait", preview: "Вопрос по интеграции с CRM — можно с менеджером?", time: "14:08", unread: 2 },
  { id: 2, name: "Дмитрий Орлов", initials: "ДО", avatarBg: "#3b82c4", product: "Foxray", channel: "TG", mode: "ai", preview: "AI: Подскажу по тарифам Foxray Про…", time: "14:07", unread: 0 },
  { id: 3, name: "Гость 8842", initials: "Г8", avatarBg: "#8c8c8c", product: "FirePage", channel: "WEB", mode: "wait", preview: "Не приходит чек на почту после оплаты", time: "13:55", unread: 1 },
  { id: 4, name: "Елена Кузнецова", initials: "ЕК", avatarBg: "#9254de", product: "Foxray", channel: "MAX", mode: "operator", preview: "Вы: Отправила счёт, жду подтверждения", time: "13:50", unread: 0 },
  { id: 5, name: "Сергей Волков", initials: "СВ", avatarBg: "#13a8a8", product: "FirePage", channel: "TG", mode: "ai", preview: "Клиент: А пробный период есть?", time: "13:42", unread: 1 },
  { id: 6, name: "Ольга Зайцева", initials: "ОЗ", avatarBg: "#d4860b", product: "Foxray", channel: "WEB", mode: "operator", preview: "Вы: Помогу с настройкой", time: "13:30", unread: 0 },
  { id: 7, name: "Павел Новиков", initials: "ПН", avatarBg: "#52a838", product: "FirePage", channel: "MAX", mode: "closed", preview: "Диалог закрыт · продажа Business", time: "12:58", unread: 0 },
  { id: 8, name: "Гость 5510", initials: "Г5", avatarBg: "#8c8c8c", product: "Foxray", channel: "TG", mode: "ai", preview: "AI: Чем могу помочь?", time: "11:20", unread: 0 },
];

export const channelMeta: Record<ChannelKey, { label: string; color: string; bg: string; handle: string }> = {
  MAX: { label: "MAX", color: "#6b5be0", bg: "#f2f0ff", handle: "@maria.s" },
  TG: { label: "Telegram", color: "#2f8fd0", bg: "#eaf6fd", handle: "@maria.s" },
  WEB: { label: "Web", color: "#0f9b8e", bg: "#e8f7f4", handle: "web-chat" },
};

export const modeDots: Record<DialogMode, string> = {
  wait: "#faad14",
  ai: "#722ed1",
  operator: "#1677ff",
  closed: "#bfbfbf",
};

export function statusFor(mode: ControlMode): StatusInfo {
  if (mode === "ai") return { label: "AI отвечает", color: "#722ed1", bg: "#f9f0ff", border: "#efdbff", dot: "#722ed1" };
  if (mode === "human") return { label: "Вы ведёте диалог", color: "#0958d9", bg: "#e6f4ff", border: "#91caff", dot: "#1677ff" };
  return { label: "Ждёт оператора", color: "#d48806", bg: "#fffbe6", border: "#ffe58f", dot: "#faad14" };
}

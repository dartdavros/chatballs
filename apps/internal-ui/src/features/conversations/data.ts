import type { ChannelKey, ControlMode, DialogMode, StatusInfo } from "./types";

export const channelMeta: Record<ChannelKey, { label: string; color: string; bg: string }> = {
  MAX: { label: "MAX", color: "#6b5be0", bg: "#f2f0ff" },
  TG: { label: "Telegram", color: "#2f8fd0", bg: "#eaf6fd" },
  WEB: { label: "Web", color: "#0f9b8e", bg: "#e8f7f4" },
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

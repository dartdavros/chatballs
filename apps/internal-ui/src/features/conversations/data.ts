import type { ControlMode, DialogMode, StatusInfo } from "./types";

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

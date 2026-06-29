import { api } from "../../api/client";

export type NotificationLevel = "INFO" | "SUCCESS" | "WARNING" | "CRITICAL";

export type AppNotification = {
  id: number;
  type: string;
  level: NotificationLevel;
  title: string;
  body: string;
  targetRoute: string;
  targetId: string;
  createdAt: string;
  unread: boolean;
};

export const LEVEL_META: Record<NotificationLevel, { color: string; icon: "bell" | "check" | "warning" | "xCircle" }> = {
  INFO: { color: "#1677ff", icon: "bell" },
  SUCCESS: { color: "#389e0d", icon: "check" },
  WARNING: { color: "#d48806", icon: "warning" },
  CRITICAL: { color: "#cf1322", icon: "xCircle" },
};

export const fetchNotifications = () => api<{ items: AppNotification[]; unreadCount: number }>("/api/v1/notifications/");
export const markRead = (ids: number[]) => api("/api/v1/notifications/read/", { method: "POST", body: JSON.stringify({ ids }) });
export const markAllRead = () => api("/api/v1/notifications/read/", { method: "POST", body: JSON.stringify({ all: true }) });

import { api } from "../../api/client";

// Активные сессии учётной записи (дизайн-базлайн v2, кадр P1): устройство,
// частично скрытый адрес и когда сессия была активна.

export type ProfileSession = {
  id: string;
  device: string;
  kind: "laptop" | "phone" | "monitor";
  address: string;
  startedAt: string | null;
  lastSeenAt: string | null;
  current: boolean;
};

export const fetchProfileSessions = () =>
  api<{ items: ProfileSession[] }>("/api/v1/auth/profile/sessions/").then((payload) => payload.items);

// «сейчас» · «2 ч назад» · «3 дня назад» — подпись справа в строке сессии.
export function lastSeenLabel(value: string | null, now = new Date()): string {
  if (!value) return "";
  const seen = new Date(value);
  if (Number.isNaN(seen.getTime())) return "";
  const minutes = Math.max(0, Math.round((now.getTime() - seen.getTime()) / 60000));
  if (minutes < 2) return "сейчас";
  if (minutes < 60) return `${minutes} мин назад`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} ч назад`;
  const days = Math.round(hours / 24);
  return days === 1 ? "вчера" : `${days} дн. назад`;
}

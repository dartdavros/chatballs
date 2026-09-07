import { api } from "../../api/client";

// Настройки инсталляции (раздел «Платформа» и карточка relay в «Голосовых и
// звонках»). Один эндпоинт на всю установку: адрес, исходящая почта и TURN.
// PATCH частичный — блоки email и turn применяются, только если пришли в теле,
// поэтому каждая карточка сохраняет свою часть и не затирает соседние.

export type EmailPayload = {
  host: string;
  port: number;
  user: string;
  hasPassword: boolean;
  useTls: boolean;
  from: string;
  configured: boolean;
};

export type InstancePayload = {
  publicHost: string;
  publicScheme: "http" | "https";
  publicUrl: string;
  updatedAt: string | null;
  email: EmailPayload;
  turn: { urls: string[]; ttlSeconds: number; secretReady: boolean };
};

export const INSTANCE_BASE = "/api/v1/company/administration/instance/";

export function loadInstance(): Promise<InstancePayload> {
  return api<{ instance: InstancePayload }>(INSTANCE_BASE).then((payload) => payload.instance);
}

export function patchInstance(body: unknown): Promise<InstancePayload> {
  return api<{ instance: InstancePayload }>(INSTANCE_BASE, {
    method: "PATCH",
    body: JSON.stringify(body),
  }).then((payload) => payload.instance);
}

// Проверка почты: отправить письмо себе и увидеть ошибку SMTP сразу, а не
// тогда, когда сотрудник не получил приглашение.
export function checkInstanceEmail(): Promise<string> {
  return api<{ sent: string }>(`${INSTANCE_BASE}email-check/`, { method: "POST", body: "{}" })
    .then((payload) => payload.sent);
}

export function instanceError(error: unknown): { detail: string; errors: Record<string, string> } {
  if (error && typeof error === "object" && "payload" in error) {
    const payload = (error as { payload?: { detail?: string; errors?: Record<string, string> } }).payload;
    return { detail: payload?.detail ?? "Не удалось сохранить", errors: payload?.errors ?? {} };
  }
  return { detail: error instanceof Error ? error.message : "Не удалось сохранить", errors: {} };
}

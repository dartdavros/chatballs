import { api } from "../../api/client";

// Обновления установки (ADR-CHATBALLS-0049): состояние канала релизов и
// установки читается одним запросом; проверку и установку запускает только
// администратор установки. Путь без организации — это свойство инсталляции.

export type InstallStatus = "IDLE" | "REQUESTED" | "RUNNING" | "DONE" | "FAILED";

export type UpdateInfo = {
  currentVersion: string;
  latestVersion: string | null;
  latestName: string;
  latestNotes: string;
  latestPublishedAt: string | null;
  latestPageUrl: string;
  available: boolean;
  checkedAt: string | null;
  checkError: string;
  updaterOnline: boolean;
  install: {
    version: string | null;
    status: InstallStatus;
    // Стадия от сервиса обновления: starting · downloading · pulling · restarting · updated,
    // либо текст ошибки.
    message: string;
    requestedAt: string | null;
    updatedAt: string | null;
  };
};

const BASE = "/api/v1/instance/update/";

export function fetchUpdate(): Promise<UpdateInfo> {
  return api<{ update: UpdateInfo }>(BASE).then((payload) => payload.update);
}

export function checkUpdates(): Promise<UpdateInfo> {
  return api<{ update: UpdateInfo }>(`${BASE}check/`, { method: "POST", body: "{}" }).then((payload) => payload.update);
}

export function installUpdate(): Promise<UpdateInfo> {
  return api<{ update: UpdateInfo }>(`${BASE}install/`, { method: "POST", body: "{}" }).then((payload) => payload.update);
}

export function installInProgress(info: UpdateInfo | null): boolean {
  return info?.install.status === "REQUESTED" || info?.install.status === "RUNNING";
}

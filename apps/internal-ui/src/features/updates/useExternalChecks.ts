import { createContext, useContext, useEffect, useRef, useState } from "react";

import { api, ApiError } from "../../api/client";
import { patchInstance, type InstancePayload } from "../settings/instance";

const ANNOUNCEMENTS_URL = "/api/v1/instance/update/announcements/";
const REFRESH_INTERVAL = 30_000;

export type ServiceAnnouncement = { id: number; title: string; text: string; link: string };

type AnnouncementResponse = {
  enabled: boolean;
  failed: boolean;
  announcements: ServiceAnnouncement[] | null;
  expiresInMs: number | null;
};

type Snapshot = Omit<AnnouncementResponse, "expiresInMs" | "failed"> & { deadline: number | null };

export function useExternalChecks(canManage: boolean) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [saveFailed, setSaveFailed] = useState(false);
  const [saving, setSaving] = useState(false);
  const reader = useRef<AbortController | null>(null);
  const enabled = snapshot?.enabled ?? null;

  useEffect(() => {
    if (!canManage || saving) return undefined;
    const controller = new AbortController();
    reader.current = controller;
    let refresh: number | undefined;

    async function read() {
      const started = Date.now();
      try {
        const { enabled, announcements, expiresInMs } = await api<AnnouncementResponse>(ANNOUNCEMENTS_URL, {
          cache: "no-store",
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        setSnapshot({ enabled, announcements, deadline: expiresInMs === null ? null : started + expiresInMs });
      } catch (error) {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
          setSnapshot(null);
        }
      }
      refresh = window.setTimeout(() => void read(), REFRESH_INTERVAL);
    }

    void read();
    return () => {
      controller.abort();
      window.clearTimeout(refresh);
    };
  }, [canManage, saving]);

  useEffect(() => {
    if (snapshot?.deadline == null) return undefined;
    const deadline = snapshot.deadline;
    const expire = () => {
      if (Date.now() < deadline) return;
      setSnapshot((current) => current === snapshot ? { ...snapshot, announcements: null, deadline: null } : current);
    };
    const timeout = window.setTimeout(expire, Math.max(0, deadline - Date.now()));
    document.addEventListener("visibilitychange", expire);
    return () => {
      window.clearTimeout(timeout);
      document.removeEventListener("visibilitychange", expire);
    };
  }, [snapshot]);

  async function toggle(nextEnabled: boolean): Promise<InstancePayload | undefined> {
    if (!canManage || saving) return undefined;
    reader.current?.abort();
    setSaving(true);
    setSaveFailed(false);
    try {
      const saved = await patchInstance({ externalChecksEnabled: nextEnabled });
      setSnapshot({ enabled: saved.externalChecksEnabled, announcements: null, deadline: null });
      return saved;
    } catch {
      setSaveFailed(true);
      return undefined;
    } finally {
      setSaving(false);
    }
  }

  const fresh = snapshot?.deadline != null && snapshot.deadline > Date.now();
  return {
    enabled,
    saving,
    saveFailed,
    announcements: canManage && enabled && fresh ? snapshot?.announcements ?? null : null,
    toggle,
  };
}

export const ExternalChecksContext = createContext<ReturnType<typeof useExternalChecks> | null>(null);

export function useShellExternalChecks() {
  const external = useContext(ExternalChecksContext);
  if (!external) throw new Error("External checks require the workspace shell");
  return external;
}

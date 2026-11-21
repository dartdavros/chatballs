import { useEffect, useRef, useState } from "react";

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

type Snapshot = Omit<AnnouncementResponse, "expiresInMs"> & { deadline: number | null };

export function useExternalChecks(
  canManage: boolean,
  savedEnabled: boolean,
  onSettingsSaved: (settings: InstancePayload) => void,
) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [readFailed, setReadFailed] = useState(false);
  const [saveFailed, setSaveFailed] = useState(false);
  const [saving, setSaving] = useState(false);
  const reader = useRef<AbortController | null>(null);
  const enabled = snapshot?.enabled ?? savedEnabled;

  useEffect(() => {
    if (!canManage || saving) return undefined;
    const controller = new AbortController();
    reader.current = controller;
    let refresh: number | undefined;

    async function read() {
      const started = Date.now();
      try {
        const { expiresInMs, ...result } = await api<AnnouncementResponse>(ANNOUNCEMENTS_URL, {
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        setSnapshot({ ...result, deadline: expiresInMs === null ? null : started + expiresInMs });
        setReadFailed(false);
      } catch (error) {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
          setSnapshot(null);
        }
        setReadFailed(true);
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

  async function toggle() {
    reader.current?.abort();
    setSaving(true);
    setSaveFailed(false);
    try {
      const saved = await patchInstance({ externalChecksEnabled: !enabled });
      setSnapshot(null);
      setReadFailed(false);
      onSettingsSaved(saved);
    } catch {
      setSaveFailed(true);
    } finally {
      setSaving(false);
    }
  }

  const fresh = snapshot?.deadline != null && snapshot.deadline > Date.now();
  return {
    enabled,
    saving,
    saveFailed,
    failed: enabled && (readFailed || Boolean(snapshot?.failed)),
    announcements: enabled && fresh ? snapshot?.announcements ?? null : null,
    toggle,
  };
}

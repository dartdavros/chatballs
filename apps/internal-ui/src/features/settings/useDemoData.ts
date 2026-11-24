import { useCallback, useEffect, useRef, useState } from "react";

import { api, ApiError } from "../../api/client";
import { t } from "../../i18n";

export type DemoStatus = "ABSENT" | "INSTALLING" | "INSTALLED" | "REINSTALLING" | "REMOVING" | "FAILED";

export type DemoAccount = {
  fullName: string;
  email: string;
  password: string;
  role: "OWNER" | "ADMIN" | "EMPLOYEE";
  positionTitle: string;
  groups: string[];
  avatarUrl: string | null;
};

export type DemoState = {
  status: DemoStatus;
  recordsCount: number;
  error: string;
  startedAt: string | null;
  finishedAt: string | null;
  accounts: DemoAccount[];
  generation: string | null;
  reinstallRequestId: string | null;
  reinstall: { status: "RUNNING" | "SUCCEEDED" | "FAILED"; errorCode: string } | null;
  northWind: boolean;
  localDemoEnabled: boolean;
};

type ReinstallCommand = {
  generation: string | null;
  previousRequestId: string | null;
  requestId: string;
};

const PATH = "/api/v1/company/demo/";
const BUSY: DemoStatus[] = ["INSTALLING", "REINSTALLING", "REMOVING"];
const POLL_INTERVAL_MS = 2000;

export function useDemoData(reload: () => void) {
  const [state, setState] = useState<DemoState | null>(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const sequence = useRef(0);
  const wasBusy = useRef(false);
  const pending = useRef<ReinstallCommand | null>(null);

  const load = useCallback(async () => {
    const read = ++sequence.current;
    try {
      const next = await api<DemoState>(PATH);
      if (read === sequence.current) setState(next);
    } catch (caught) {
      if (caught instanceof ApiError && [401, 403, 404].includes(caught.status)) {
        const session = await api<{ authenticated: boolean }>("/api/v1/auth/session/").catch(() => null);
        if (read === sequence.current && session?.authenticated === false) {
          window.location.reload();
          return;
        }
      }
      if (read === sequence.current) {
        setError(caught instanceof Error ? caught.message : t("settings.could_not_read_demo_data"));
      }
    }
  }, []);

  useEffect(() => {
    void load();
    return () => { sequence.current += 1; };
  }, [load]);

  const busy = state !== null && BUSY.includes(state.status);
  useEffect(() => {
    if (!busy) return undefined;
    const timer = window.setInterval(() => void load(), POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [busy, load]);

  useEffect(() => {
    if (!busy && wasBusy.current) reload();
    wasBusy.current = busy;
  }, [busy, reload]);

  async function submit(action: "install" | "remove" | "reinstall"): Promise<boolean> {
    sequence.current += 1;
    setSubmitting(true);
    setError("");
    try {
      const command = action === "reinstall" && state ? getReinstallCommand(state) : null;
      const next = await api<DemoState>(command ? `${PATH}reinstall/` : PATH, {
        method: action === "remove" ? "DELETE" : "POST",
        body: command ? JSON.stringify(command) : undefined,
      });
      pending.current = null;
      setState(next);
      return true;
    } catch (caught) {
      const fallback = {
        install: t("settings.could_not_start_installation"),
        remove: t("settings.could_not_start_removal"),
        reinstall: t("settings.demo_reinstall_failed"),
      };
      setError(caught instanceof Error ? caught.message : fallback[action]);
      if (action === "reinstall") void load();
      return false;
    } finally {
      setSubmitting(false);
    }
  }

  function getReinstallCommand(snapshot: DemoState): ReinstallCommand {
    const generation = snapshot.generation;
    const previousRequestId = snapshot.reinstallRequestId;
    if (pending.current?.generation === generation && pending.current.previousRequestId === previousRequestId) {
      return pending.current;
    }
    pending.current = { generation, previousRequestId, requestId: crypto.randomUUID() };
    return pending.current;
  }

  return { state, busy, error, submitting, submit };
}

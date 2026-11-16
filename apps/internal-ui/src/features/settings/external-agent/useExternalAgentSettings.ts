import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "../../../api/client";
import { configurationChanges } from "./bindings";
import { changeFeature, connectionAction, createConnection, fetchSettings, pathFor,
  type AccessDraft, type ConnectionDraft, type ExternalConnection, type ExternalSettings } from "./model";

export function useExternalAgentSettings(organization: string) {
  const [settings, setSettings] = useState<ExternalSettings>();
  const [failed, setFailed] = useState(false);
  const [forbidden, setForbidden] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<"load" | "enable" | "save" | "check" | null>(null);
  const [incomingKey, setIncomingKey] = useState<string>();
  const [checkFailure, setCheckFailure] = useState<"access" | "unavailable" | "incompatible">("unavailable");
  const [activeConnectionId, setActiveConnectionId] = useState<number>();
  const [operationKind, setOperationKind] = useState<"load" | "enable" | "save" | "check">();
  const [featureFailure, setFeatureFailure] = useState<"enable" | "save" | null>(null);
  const alive = useRef(true);
  const pending = useRef(false);
  const reload = useCallback(async (signal?: AbortSignal) => {
    setFailed(false); setForbidden(false);
    try { const loaded = await fetchSettings(organization, signal); if (!signal?.aborted && alive.current) setSettings(loaded); }
    catch (caught) { if (!signal?.aborted && alive.current) { setFailed(true); setForbidden(caught instanceof ApiError && caught.status === 403); } }
  }, [organization]);
  useEffect(() => {
    alive.current = true;
    const controller = new AbortController();
    void reload(controller.signal);
    return () => { alive.current = false; controller.abort(); };
  }, [reload]);
  async function perform(kind: NonNullable<typeof error>, operation: () => Promise<void>, id?: number) {
    if (pending.current) return false;
    pending.current = true; setFeatureFailure(null); setOperationKind(kind); setActiveConnectionId(id); setBusy(true); setError(null);
    try { await operation(); return true; }
    catch (caught) {
      if (alive.current) {
        setError(kind);
        const failure = caught instanceof ApiError ? caught.payload.failure : undefined;
        setCheckFailure(failure === "access" || failure === "incompatible" ? failure : "unavailable");
      }
      return false;
    }
    finally { pending.current = false; if (alive.current) setBusy(false); }
  }
  async function feature(enabled: boolean) {
    const ok = await perform(enabled ? "enable" : "save", async () => {
      const updated = await changeFeature(organization, enabled);
      if (alive.current) setSettings(updated);
    });
    if (!ok && alive.current) setFeatureFailure(enabled ? "enable" : "save");
    return ok;
  }
  const create = (draft: AccessDraft, after?: "key" | "check") => perform(after === "check" ? "check" : "save", async () => {
    const created = await createConnection(organization, draft);
    try {
      if (after) {
        const result = await connectionAction(organization, created.connection.id, after);
        if (result?.incomingKey && alive.current) setIncomingKey(result.incomingKey);
      }
    } finally { await reload(); }
  });
  const save = (previous: ExternalConnection, draft: ConnectionDraft) => perform("save", async () => {
    const updated = await api<ExternalSettings>(`${pathFor(organization)}connections/${draft.id}/configuration/`, {
      method: "PUT", body: JSON.stringify(configurationChanges(previous, draft)),
    });
    if (alive.current) setSettings(updated);
  }, draft.id);
  const action = (id: number, actionName: "check" | "key", method = "POST", onChecked?: (connection: ExternalConnection) => void) => perform(actionName === "check" ? "check" : "save", async () => {
    try {
      const result = await connectionAction(organization, id, actionName, method);
      if (actionName === "check" && result && alive.current) onChecked?.(result.connection);
      if (result?.incomingKey && alive.current) setIncomingKey(result.incomingKey);
    } finally { await reload(); }
  }, id);
  return { settings, failed, forbidden, busy, error, operationKind, featureFailure, checkFailure, activeConnectionId, reload, feature, create, save, action, incomingKey,
    dismissKey: () => setIncomingKey(undefined) };
}

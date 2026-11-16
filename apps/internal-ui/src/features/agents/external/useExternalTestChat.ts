import { useEffect, useRef, useState } from "react";
import { api } from "../../../api/client";
import type { TestValues } from "../test-chat/model";
import { testData, type TestDefinition, type ExternalTestSession } from "./test-model";

export function useExternalTestChat(agentId: number) {
  const base = `/api/v1/agents/${agentId}/external-test/`;
  const [definition, setDefinition] = useState<TestDefinition>();
  const [session, setSession] = useState<ExternalTestSession>();
  const [values, setValues] = useState<TestValues>({});
  const [failed, setFailed] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [busy, setBusy] = useState(false);
  const mounted = useRef(false), pending = useRef(false), scope = useRef<string | undefined>(undefined);
  const generation = useRef(0);
  async function load(signal?: AbortSignal) {
    setLoadError(false);
    try { const result = await api<TestDefinition>(base, { signal }); if (!signal?.aborted) setDefinition(result); }
    catch { if (!signal?.aborted) setLoadError(true); }
  }
  useEffect(() => {
    mounted.current = true;
    const controller = new AbortController();
    void load(controller.signal);
    return () => {
      mounted.current = false; controller.abort(); generation.current++;
      if (scope.current) void api(`${base}${scope.current}/`, { method: "DELETE" }).catch(() => undefined);
    };
  }, [base]);
  useEffect(() => {
    if (!session) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const result = await api<ExternalTestSession>(`${base}${session!.id}/`, { signal: controller.signal });
        if (!controller.signal.aborted && scope.current === result.id) setSession(result);
      } catch { if (!controller.signal.aborted) setFailed(true); }
      if (!controller.signal.aborted) timer = setTimeout(() => void poll(), 3000);
    }
    timer = setTimeout(() => void poll(), 1000);
    return () => { controller.abort(); clearTimeout(timer); };
  }, [base, session?.id]);
  async function send(message: string) {
    if (pending.current || !definition) return false;
    pending.current = true; setBusy(true); setFailed(false);
    const current = generation.current;
    try {
      let id = scope.current;
      if (!id) {
        const created = await api<ExternalTestSession>(base, { method: "POST", body: JSON.stringify({ clientData: testData(definition, values) }) });
        id = created.id;
        if (!mounted.current || current !== generation.current) {
          void api(`${base}${id}/`, { method: "DELETE" }).catch(() => undefined); return false;
        }
        scope.current = id; setSession(created);
      }
      const result = await api<ExternalTestSession>(`${base}${id}/`, { method: "POST", body: JSON.stringify({ message }) });
      if (mounted.current && current === generation.current) setSession(result);
      return true;
    } catch { if (mounted.current && current === generation.current) setFailed(true); return false; }
    finally { pending.current = false; if (mounted.current) setBusy(false); }
  }
  async function restart() {
    if (pending.current) return;
    pending.current = true; setBusy(true);
    try {
      if (scope.current) await api(`${base}${scope.current}/`, { method: "DELETE" });
      scope.current = undefined; generation.current++; setSession(undefined); setFailed(false); void load();
    } catch { setFailed(true); }
    finally { pending.current = false; if (mounted.current) setBusy(false); }
  }
  return { definition, session, values, setValues, failed, loadError, busy, send, restart, reload: () => void load(), base };
}

import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "../../../api/client";
import { t } from "../../../i18n";
import type { Integration } from "../../integrations/model";
import { chatHistory, clientData, displayReply, testConnections, type TestConnection, type TestReply, type TestTurn, type TestValues } from "./model";

export function useAgentTestChat(agentId: number) {
  const [connections, setConnections] = useState<TestConnection[]>();
  const [loadError, setLoadError] = useState(false);
  const [values, setValues] = useState<TestValues>({});
  const [turns, setTurns] = useState<TestTurn[]>([]);
  const [busy, setBusy] = useState(false);
  const [executionMode, setExecutionMode] = useState<"preview" | "execute">("preview");
  const controller = useRef<AbortController | null>(null);

  async function load(signal?: AbortSignal) {
    setLoadError(false);
    try {
      const payload = await api<{ items: Integration[] }>("/api/v1/integrations/", { signal });
      if (!signal?.aborted) setConnections(testConnections(payload.items, agentId));
    } catch {
      if (!signal?.aborted) setLoadError(true);
    }
  }

  useEffect(() => {
    const loading = new AbortController();
    void load(loading.signal);
    return () => { loading.abort(); controller.current?.abort(); };
  }, [agentId]);

  async function send(message: string) {
    if (controller.current || !connections || !message.trim()) return;
    const request = new AbortController();
    controller.current = request;
    setBusy(true);
    const turn: TestTurn = { message: message.trim(), calls: [], createdAt: new Date().toISOString() };
    setTurns((current) => [...current, turn]);
    try {
      const result = await api<TestReply>(`/api/v1/agents/${agentId}/test-chat/`, {
        method: "POST", signal: request.signal,
        body: JSON.stringify({ message: turn.message, history: chatHistory(turns), clientData: clientData(values, connections), executionMode }),
      });
      if (!request.signal.aborted) setTurns((current) => [...current.slice(0, -1), {
        ...turn, formatVersion: result.formatVersion, presentation: result.presentation,
        deliveryRepresentation: result.deliveryRepresentation, template: result.template,
        reply: displayReply(result.reply), calls: result.toolCalls ?? [], serviceActions: result.serviceActions,
      }]);
    } catch (caught) {
      if (!request.signal.aborted) {
        const error = caught instanceof ApiError && caught.status < 500
          ? caught.payload.detail ?? t("conversations.could_not_send_message")
          : t("conversations.could_not_send_message");
        const calls = caught instanceof ApiError && Array.isArray(caught.payload.toolCalls) ? caught.payload.toolCalls as TestReply["toolCalls"] : [];
        const serviceActions = caught instanceof ApiError && Array.isArray(caught.payload.serviceActions) ? caught.payload.serviceActions as TestReply["serviceActions"] : [];
        setTurns((current) => [...current.slice(0, -1), { ...turn, error, calls, serviceActions }]);
      }
    } finally {
      if (controller.current === request) { controller.current = null; setBusy(false); }
    }
  }

  function restart() {
    controller.current?.abort();
    controller.current = null;
    setBusy(false);
    setTurns([]);
  }

  return { connections, loadError, reload: () => void load(), values, setValues, turns, busy, send, restart, executionMode, setExecutionMode };
}

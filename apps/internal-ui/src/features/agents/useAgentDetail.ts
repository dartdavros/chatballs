import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../../api/client";
import { t } from "../../i18n";
import { fetchAgentProviders, type Integration } from "../integrations/model";
import { useAgentTools } from "./useAgentTools";
import { fetchAgent, patchAgent, setAgentAiActive, deleteAgent, bindAgentConnection, unbindAgentConnection, type AgentCard, type AgentPatch } from "./model";

type Feedback = { kind: "error" | "warning"; text: string } | null;

function useAgentCard(agentId: number | null) {
  const [card, setCard] = useState<AgentCard | null>(null);
  const [missing, setMissing] = useState(false);
  const [failed, setFailed] = useState(false);

  const load = useCallback(async () => {
    if (!agentId) {
      setMissing(true);
      return;
    }
    try {
      const payload = await fetchAgent(agentId);
      setCard(payload.agent);
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 404) setMissing(true);
      else setFailed(true);
    }
  }, [agentId]);

  useEffect(() => {
    void load();
  }, [load]);

  return { card, setCard, missing, failed, reload: load };
}

export function useAgentDetail(agentId: number | null, canManage: boolean, canManageConnections: boolean, openAgents: () => void) {
  const { card, setCard, missing, failed, reload } = useAgentCard(agentId);
  const tools = useAgentTools(agentId);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<Feedback>(null);
  const [deleting, setDeleting] = useState(false);
  const [providers, setProviders] = useState<Integration[]>([]);
  const [messengers, setMessengers] = useState<Integration[]>([]);

  const loadMessengers = useCallback(async () => {
    try {
      const payload = await api<{ items: Integration[] }>("/api/v1/integrations/");
      setMessengers(payload.items.filter((item) => item.kind === "MESSENGER" && !item.config.purpose));
    } catch {
      setMessengers([]);
    }
  }, []);

  useEffect(() => {
    if (canManage) fetchAgentProviders().then(setProviders).catch(() => setProviders([]));
  }, [canManage]);

  useEffect(() => {
    if (canManageConnections) void loadMessengers();
  }, [canManageConnections, loadMessengers]);

  async function apply(patch: AgentPatch, showFeedback = true) {
    setBusy(true);
    setFeedback(null);
    try {
      const saved = await patchAgent(card!.id, patch);
      setCard(saved.agent);
      tools.adopt(saved.agent.tools);
      return true;
    } catch (caught) {
      if (showFeedback) setFeedback({
        kind: "error",
        text: caught instanceof ApiError ? caught.payload.detail ?? t("common.could_not_save") : t("common.could_not_save"),
      });
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function toggleAi() {
    setBusy(true);
    setFeedback(null);
    try {
      const saved = await setAgentAiActive(card!.id, card!.aiStatus !== "ACTIVE");
      setCard(saved.agent);
    } catch (caught) {
      setFeedback({
        kind: "error",
        text: caught instanceof ApiError && caught.payload.detail
          ? caught.payload.detail
          : t("ai.could_not_change_ai_status"),
      });
    } finally {
      setBusy(false);
    }
  }

  async function removeAgent() {
    setBusy(true);
    try {
      await deleteAgent(card!.id);
      openAgents();
    } catch (caught) {
      setDeleting(false);
      setFeedback({
        kind: "warning",
        text:
          caught instanceof ApiError && caught.status === 409
            ? t("ai.agent_cannot_deleted_has_conversations")
            : t("ai.could_not_delete_agent"),
      });
    } finally {
      setBusy(false);
    }
  }

  async function unbind(integrationId: number) {
    setBusy(true);
    try {
      const saved = await unbindAgentConnection(card!.id, integrationId);
      setCard(saved.agent);
      void loadMessengers();
    } catch {
      setFeedback({ kind: "error", text: t("ai.could_not_detach_connection") });
    } finally {
      setBusy(false);
    }
  }

  async function bind(integrationId: number) {
    setBusy(true);
    setFeedback(null);
    try {
      const saved = await bindAgentConnection(card!.id, integrationId);
      setCard(saved.agent);
      void loadMessengers();
    } catch (caught) {
      setFeedback({
        kind: "error",
        text:
          caught instanceof ApiError && caught.status === 409
            ? t("ai.connection_already_bound_another_agent")
            : t("ai.could_not_bind_connection"),
      });
    } finally {
      setBusy(false);
    }
  }

  const saveAssistance = (enabled: boolean) => apply({ assistanceEnabled: enabled }, false);

  return { card, missing, failed, reload, tools, busy, feedback, deleting, setDeleting, providers, messengers, apply, saveAssistance, toggleAi, removeAgent, bind, unbind };
}

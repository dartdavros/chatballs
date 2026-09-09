import { isTerminalCallStatus } from "@chatballs/ui";
import { useCallback, useEffect, useRef, useState } from "react";

import {
  cancelCall,
  fetchActiveCall,
  fetchCall,
  fetchStaffCallAccess,
  requestCall,
  type ApiCall,
  type CallAccess,
  type CallKind,
} from "./model";
import { t } from "../../i18n";

type Options = {
  conversationId: number | null;
  onConversationChanged: () => void;
};

export function useConversationCall({ conversationId, onConversationChanged }: Options) {
  const [open, setOpen] = useState(false);
  const [call, setCall] = useState<ApiCall | null>(null);
  const [access, setAccess] = useState<CallAccess | null>(null);
  const [errorText, setErrorText] = useState("");
  const [busy, setBusy] = useState(false);
  const [requestedKind, setRequestedKind] = useState<CallKind | null>(null);
  const lastKind = useRef<CallKind>("AUDIO");

  const reset = useCallback(() => {
    setOpen(false);
    setCall(null);
    setAccess(null);
    setErrorText("");
    setRequestedKind(null);
  }, []);

  useEffect(() => reset(), [conversationId, reset]);

  useEffect(() => {
    if (!open || !call || isTerminalCallStatus(call.status)) return;
    const timer = setInterval(async () => {
      try { setCall(await fetchCall(call.id)); } catch { /* transient */ }
    }, 2000);
    return () => clearInterval(timer);
  }, [open, call?.id, call?.status]);

  const ensureAccess = useCallback(async (callId: string) => {
    const next = await fetchStaffCallAccess(callId);
    setAccess(next);
    return next;
  }, []);

  const start = useCallback(async (kind: CallKind = "AUDIO") => {
    if (conversationId == null || busy) return;
    lastKind.current = kind;
    setRequestedKind(kind);
    setBusy(true);
    setErrorText("");
    try {
      const active = await fetchActiveCall(conversationId);
      if (active) {
        if (active.kind !== kind) {
          const activeLabel = active.kind === "AUDIO" ? t("conversations.audio_call_2") : t("conversations.video_call");
          throw new Error(t("conversations.finish_current_call_first", { kind: activeLabel }));
        }
        setCall(active);
        await ensureAccess(active.id);
      } else {
        const created = await requestCall(conversationId, kind);
        setCall(created.call);
        setAccess(created.access);
      }
      onConversationChanged();
    } catch (error) {
      setCall(null);
      setAccess(null);
      setErrorText(error instanceof Error ? error.message : t("conversations.could_not_request_call"));
    } finally {
      setBusy(false);
      setOpen(true);
    }
  }, [busy, conversationId, ensureAccess, onConversationChanged]);

  const cancel = useCallback(async () => {
    if (!call) return;
    try {
      setCall(await cancelCall(call.id));
      onConversationChanged();
      setOpen(false);
    } catch (error) {
      setErrorText(error instanceof Error ? error.message : t("conversations.could_not_cancel_call"));
    }
  }, [call, onConversationChanged]);

  const retry = useCallback(async () => {
    if (conversationId == null) return;
    setCall(null);
    setAccess(null);
    setErrorText("");
    setRequestedKind(lastKind.current);
    try {
      const created = await requestCall(conversationId, lastKind.current);
      setCall(created.call);
      setAccess(created.access);
      onConversationChanged();
    } catch (error) {
      setErrorText(error instanceof Error ? error.message : t("conversations.could_not_request_call"));
    }
  }, [conversationId, onConversationChanged]);

  return {
    open,
    call,
    access,
    errorText,
    busy,
    requestedKind,
    start,
    cancel,
    retry,
    close: () => setOpen(false),
    setCall,
  };
}

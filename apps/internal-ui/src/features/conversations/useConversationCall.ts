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

const TERMINAL = new Set(["DECLINED", "CANCELLED", "MISSED", "ENDED", "FAILED", "EXPIRED"]);

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
    if (!open || !call || TERMINAL.has(call.status)) return;
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
          const activeLabel = active.kind === "AUDIO" ? "аудиозвонок" : "видеозвонок";
          throw new Error(`Сначала завершите текущий ${activeLabel}`);
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
      setErrorText(error instanceof Error ? error.message : "Не удалось запросить звонок");
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
      setErrorText(error instanceof Error ? error.message : "Не удалось отменить звонок");
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
      setErrorText(error instanceof Error ? error.message : "Не удалось запросить звонок");
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

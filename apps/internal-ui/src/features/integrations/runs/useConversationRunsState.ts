import { useEffect, useRef, useState } from "react";
import type { EntityLink } from "../entity-links/api";
import { createConversationSelection, type ConversationSelectionToken } from "./conversationSelection";
import type { ManualAction, ManualActionDetail, ManualCatalog } from "./types";
import { useConversationRunHistory } from "./useConversationRunHistory";

export type ConversationRunSheet = {
  conversationId: number; token: ConversationSelectionToken; busy: boolean;
  action?: ManualAction; catalog?: ManualCatalog; runId?: string; link?: EntityLink;
};
type SheetContent = Pick<ConversationRunSheet, "action" | "catalog" | "runId" | "link">;

export function useConversationRunsState(conversationId: number | null) {
  const history = useConversationRunHistory(conversationId);
  const gateRef = useRef<ReturnType<typeof createConversationSelection> | null>(null);
  if (!gateRef.current) gateRef.current = createConversationSelection(conversationId);
  const gate = gateRef.current;
  const context = gate.enter(conversationId);
  const active = useRef(false);
  const [storedSheet, setStoredSheet] = useState<ConversationRunSheet | null>(null);
  const sheetRef = useRef<ConversationRunSheet | null>(null);
  useEffect(() => { active.current = true; return () => { active.current = false; }; }, []);
  const sheet = storedSheet && gate.isCurrent(storedSheet.token) ? storedSheet : null;
  const live = () => active.current && gate.isContext(context);
  const current = (expected: ConversationRunSheet) => live() && gate.isCurrent(expected.token);
  const open = (content: SheetContent) => {
    if (!live() || conversationId === null) return;
    const token = gate.begin(context);
    if (!token) return;
    const next = { ...content, token, conversationId, busy: false };
    sheetRef.current = next;
    setStoredSheet(next);
  };
  const close = () => {
    if (!live() || (sheetRef.current && gate.isCurrent(sheetRef.current.token) && sheetRef.current.busy)) return;
    gate.close(context);
    sheetRef.current = null;
    setStoredSheet(null);
  };
  const setBusy = (expected: ConversationRunSheet, busy: boolean) => {
    if (!current(expected) || !sheetRef.current || sheetRef.current.busy === busy) return;
    const next = { ...sheetRef.current, busy };
    sheetRef.current = next;
    setStoredSheet(next);
  };
  const showCompletedRun = (expected: ConversationRunSheet, runId: string) => {
    if (!current(expected)) return;
    open({ runId });
    void history.refresh();
  };
  const finishLink = (expected: ConversationRunSheet) => {
    if (!current(expected)) return;
    close();
    void history.refresh();
  };
  return { ...history, conversationId, sheet, close, setBusy, showCompletedRun, finishLink,
    openAction: ({ item, files }: ManualActionDetail) => open({ action: item, catalog: { items: [item], files } }),
    openRun: (runId: string) => open({ runId }), openLink: (link: EntityLink) => open({ link }) };
}

import { useEffect, useState } from "react";
import { t } from "../../../i18n";
import { Button } from "../../../shared/ui-controls";
import { useConversationRuns } from "./conversationContext";
import { ManualActionPicker } from "./ManualActionPicker";
import "./manual-action-menu.css";

export function ManualActionMenu({ conversationTitle }: { conversationTitle?: string }) {
  const state = useConversationRuns();
  const conversationId = state?.conversationId ?? null;
  const [openedFor, setOpenedFor] = useState<number | null>(null);
  useEffect(() => setOpenedFor(null), [conversationId]);
  if (!state || conversationId === null) return null;
  return <>
    <Button variant="secondary" className="row-menu-button run-launch-trigger" icon="plug" disabled={state.sheet?.busy}
      aria-label={t("runs.actions")} aria-haspopup="dialog" onClick={() => setOpenedFor(conversationId)}>
      <span className="run-launch-label">{t("runs.actions")}</span>
    </Button>
    {openedFor === conversationId && <ManualActionPicker key={conversationId} conversationId={conversationId} conversationTitle={conversationTitle}
      onClose={() => setOpenedFor(null)} onSelected={detail => { state.openAction(detail); setOpenedFor(null); }} />}
  </>;
}

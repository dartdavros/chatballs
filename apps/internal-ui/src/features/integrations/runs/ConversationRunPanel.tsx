import type { ReactNode } from "react";
import { t } from "../../../i18n";
import { IconButton } from "../../../shared/ui-controls";
import { useMediaQuery } from "../../../shared/useMediaQuery";
import { useConversationRuns } from "./conversationContext";
import { ManualLaunch } from "./ManualLaunch";
import { RunDetail } from "./RunDetail";
import { LinkSearch } from "../entity-links/LinkSearch";

export function ConversationRunContent() {
  const state = useConversationRuns();
  const sheet = state?.sheet;
  if (!state || !sheet) return null;
  if (sheet.link) return <LinkSearch key={sheet.token.sequence} link={sheet.link} conversation={sheet.conversationId} done={() => state.finishLink(sheet)} />;
  if (sheet.action && sheet.catalog) return <ManualLaunch key={sheet.token.sequence} action={sheet.action}
    conversationId={sheet.conversationId} catalog={sheet.catalog} onClose={state.close} launchPending={sheet.busy}
    onBusyChange={busy => state.setBusy(sheet, busy)} onRun={id => state.showCompletedRun(sheet, id)} />;
  return sheet.runId ? <RunDetail key={sheet.token.sequence} id={sheet.runId} inChat onBack={state.close} onRepeated={id => state.showCompletedRun(sheet, id)} /> : null;
}

export function ConversationRunPanel({ children }: { children: ReactNode }) {
  const state = useConversationRuns();
  const mobile = useMediaQuery("(max-width: 767px)");
  if (!state?.sheet || mobile) return children;
  return <aside className="sales-context run-context-panel"><header><h3>{state.sheet.link ? t("runs.replace_link") : state.sheet.action?.title ?? t("runs.details")}</h3>
    <IconButton bare icon="close" label={t("common.close")} disabled={state.sheet.busy} onClick={state.close} /></header>
    <div className="run-context-body"><ConversationRunContent /></div></aside>;
}

import { useState } from "react";
import { t } from "../../../i18n";
import { DecisionDialog } from "../../../shared/DecisionDialog";
import { EmptyState, LoadingState } from "../../../shared/ui";
import { Button } from "../../../shared/ui-controls";
import { ScenarioDrawer } from "./ScenarioDrawer";
import { ScenarioHeader } from "./ScenarioHeader";
import { ScenarioList } from "./ScenarioList";
import { ScenarioSections } from "./ScenarioSections";
import { useScenarioEditor } from "./useScenarioEditor";
import "./scenarios.css";
import { RunsWorkspace } from "../runs/RunsWorkspace";

export function ScenariosWorkspace({ initial }: { initial?: string }) {
  const editor = useScenarioEditor(initial);
  const [journal, setJournal] = useState(new URLSearchParams(location.search).has("runs"));
  const showJournal = (show: boolean) => { const url = new URL(location.href); if (show) url.searchParams.set("runs", "1"); else { url.searchParams.delete("runs"); url.searchParams.delete("run"); } history.replaceState(history.state, "", url); setJournal(show); };
  const [deleting, setDeleting] = useState(false);
  if (journal) return <RunsWorkspace onScenarios={() => showJournal(false)} />;
  return <div className="scenario-workspace">
    {editor.loading ? <LoadingState /> : !editor.catalog || editor.error && !editor.draft ? <EmptyState title={editor.error || t("scenarios.load_failed")} />
      : editor.draft ? <><ScenarioHeader editor={editor} onDelete={() => setDeleting(true)} /><fieldset className="scenario-fieldset" disabled={editor.saving}><ScenarioSections editor={editor} /></fieldset><ScenarioDrawer editor={editor} /></>
      : <ScenarioList rows={editor.rows} catalog={editor.catalog} open={editor.open} openJournal={() => showJournal(true)} />}
    <DecisionDialog open={Boolean(editor.pendingLeave)} tone="warning" icon="warning" title={t("scenarios.leave_title")}
      description={t("scenarios.leave_text")} onClose={() => editor.setPendingLeave(null)} actions={<>
        <Button variant="secondary" onClick={() => editor.setPendingLeave(null)}>{t("scenarios.cancel")}</Button>
        <button type="button" className="link is-muted" disabled={editor.saving} onClick={() => editor.pendingLeave?.()}>{t("scenarios.leave_discard")}</button>
        <Button variant="primary" disabled={editor.saving} onClick={async () => { if (await editor.save()) editor.pendingLeave?.(); }}>{t("scenarios.save")}</Button>
      </>} />
    <DecisionDialog open={deleting} tone="danger" icon="trash" title={t("scenarios.delete_title")} description={t("scenarios.delete_text")}
      onClose={() => setDeleting(false)} actions={<><Button variant="secondary" onClick={() => setDeleting(false)}>{t("scenarios.cancel")}</Button>
        <Button variant="danger-outline" disabled={editor.saving} onClick={async () => { if (await editor.remove()) setDeleting(false); }}>{t("scenarios.delete")}</Button></>} />
  </div>;
}

import type { ReactNode } from "react";
import { t } from "../../../i18n";
import { Icon } from "../../../shared/icons";
import { StepList } from "./StepList";
import { conditionSummary, newCondition } from "./conditionModel";
import { presentIssue } from "./issuePresentation";
import type { ScenarioEditorState } from "./useScenarioEditor";

function Section({ title, lead, children }: { title: string; lead: string; children: ReactNode }) {
  return <section className="scenario-section"><header><strong>{title}</strong><span>{lead}</span></header>{children}</section>;
}
export function ScenarioSections({ editor }: { editor: Pick<ScenarioEditorState,
  "draft" | "catalog" | "error" | "conflict" | "issues" | "reload" | "setDrawer" | "mutate"> }) {
  const { draft, catalog } = editor;
  if (!draft || !catalog) return null;
  return <div className="scenario-sections">
    {draft.externalKeys?.some(key => key.key) && <div className="scenario-banner"><strong>{t("scenarios.key_created")}</strong>
      <p>{t("scenarios.key_fresh")}</p><button type="button" className="link" onClick={() => editor.setDrawer({ kind: "trigger", id: draft.externalKeys!.find(key => key.key)!.trigger })}>{t("scenarios.key_show")}</button></div>}
    {(editor.error || editor.conflict || editor.issues.length > 0) && <div className="scenario-banner" role="alert">
      {editor.conflict || editor.error && !editor.issues.length ? <p>{editor.conflict ? t("scenarios.conflict") : editor.error}</p>
        : <div className="scenario-issue-list">{editor.issues.map((issue, index) => {
          const shown = presentIssue(issue, draft.definition, catalog);
          return shown.block ? <button type="button" className="link is-neutral" key={index} onClick={() => editor.setDrawer({ kind: "block", id: shown.block! })}>{shown.message}</button>
            : <p key={index}>{shown.message}</p>;
        })}</div>}
      {editor.conflict && <button type="button" className="link" onClick={() => void editor.reload()}>{t("scenarios.reload")}</button>}
    </div>}
    <Section title={t("scenarios.launch")} lead={t("scenarios.launch_lead")}>
      {draft.definition.triggers.map(trigger => <button className="scenario-trigger" type="button" key={trigger.id}
        onClick={() => editor.setDrawer({ kind: "trigger", id: trigger.id })}>
        <span className="scenario-trigger-icon"><Icon name={trigger.kind === "schedule" ? "clock" : trigger.kind === "ai" ? "sparkles" : "play"} size={16} /></span>
        <span><strong>{t(`scenarios.trigger_${trigger.kind}`)}</strong><small>{trigger.kind === "schedule" ? [trigger.time, trigger.timezone].join(" · ")
          : catalog.connections.find(c => String(c.id) === trigger.connection)?.name}</small></span><Icon name="chevronRight" size={16} />
      </button>)}
      <button type="button" className="link has-icon" onClick={() => editor.setDrawer({ kind: "addTrigger" })}><Icon name="plus" size={14} />{t("scenarios.add_trigger")}</button>
    </Section>
    <Section title={t("scenarios.conditions")} lead={t("scenarios.conditions_lead")}>
      {draft.definition.conditions.items.map((condition, index) => <button type="button" className="scenario-condition-summary" key={index}
        onClick={() => editor.setDrawer({ kind: "condition", index })}>
        <Icon name="gitBranch" size={16} /><span>{conditionSummary(condition, draft.definition, catalog)}</span><Icon name="chevronRight" size={14} />
      </button>)}
      <button type="button" className="link has-icon" onClick={() => {
        editor.mutate(document => document.conditions.items.push(newCondition("contact", [])));
        editor.setDrawer({ kind: "condition", index: draft.definition.conditions.items.length });
      }}><Icon name="plus" size={14} />{t("scenarios.add_condition")}</button>
    </Section>
    <Section title={t("scenarios.steps")} lead={t("scenarios.steps_lead")}>
      <StepList steps={draft.definition.steps} catalog={catalog} document={draft.definition} onChange={steps => editor.mutate(document => { document.steps = steps; })}
        onOpen={id => editor.setDrawer({ kind: "block", id })} onAdd={location => editor.setDrawer({ kind: "add", location })} />
    </Section>
  </div>;
}

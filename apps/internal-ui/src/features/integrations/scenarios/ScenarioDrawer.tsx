import { Drawer } from "antd";
import { t } from "../../../i18n";
import { Icon } from "../../../shared/icons";
import { Button, IconButton } from "../../../shared/ui-controls";
import { BlockEditor } from "./BlockEditor";
import { ConditionsEditor } from "./ConditionsEditor";
import { ExternalKeyFields } from "./ExternalKeyFields";
import { findBlock, id, listAt, newBlock, operations, blockTitle, blockPath } from "./model";
import { TriggerEditor } from "./TriggerEditor";
import type { BlockKind, TriggerKind } from "./types";
import type { ScenarioEditorState } from "./useScenarioEditor";

export function ScenarioDrawer({ editor }: { editor: Pick<ScenarioEditorState,
  "drawer" | "draft" | "catalog" | "hideKeys" | "setDrawer" | "mutate" | "saving" | "issues" | "setDraft" | "dirty" | "rotateKey"> }) {
  const { drawer, draft, catalog } = editor;
  if (!drawer || !draft || !catalog) return null;
  const block = drawer.kind === "block" ? findBlock(draft.definition.steps, drawer.id) : undefined;
  const trigger = drawer.kind === "trigger" ? draft.definition.triggers.find(t => t.id === drawer.id) : undefined;
  const title = block ? blockTitle(block, catalog) : trigger ? t(`scenarios.trigger_${trigger.kind}`)
    : t(drawer.kind === "add" ? "scenarios.add_step" : drawer.kind === "addTrigger" ? "scenarios.add_trigger" : "scenarios.conditions");
  const close = () => { editor.hideKeys(); editor.setDrawer(null); };
  function insert(kind: BlockKind, connection?: string, target?: string) {
    if (drawer?.kind !== "add") return;
    const step = { ...newBlock(kind), ...(connection ? { connection, target } : {}) };
    editor.mutate(document => listAt(document.steps, drawer.location).push(step));
    editor.setDrawer({ kind: "block", id: step.id });
  }
  function addTrigger(kind: TriggerKind) {
    const trigger = { id: id(), kind, ...(kind === "schedule" ? { frequency: "daily" as const, timezone: catalog!.timezone,
      time: "09:00", misfire: "once" as const, ambiguous: "first" as const, nonexistent: "skip" as const } : {}) };
    editor.mutate(document => document.triggers.push(trigger)); editor.setDrawer({ kind: "trigger", id: trigger.id });
  }
  return <Drawer open width={480} closable={false} onClose={close} className="scenario-drawer"
    title={title} extra={<IconButton icon="close" label={t("common.close")} onClick={close} />}
    footer={<Button variant="primary" onClick={close}>{t("scenarios.done")}</Button>}>
    <fieldset className="scenario-form scenario-fieldset" disabled={editor.saving}>
      {drawer.kind === "add" && <>
        {[{ id: "chatballs", name: t("scenarios.chatballs") }, ...catalog.connections.map(c => ({ id: String(c.id), name: c.name }))].map(connection => <div className="scenario-palette" key={connection.id}>
          <strong>{connection.name}</strong>{operations(catalog, connection.id).map(operation => <button type="button" key={operation.key}
            onClick={() => insert("action", connection.id, operation.key)}>{operation.title}<Icon name="chevronRight" size={14} /></button>)}
        </div>)}
        <div className="scenario-palette"><strong>{t("scenarios.advanced")}</strong>
          {(["if", "foreach", "parallel", "call", "wait", "try"] as const).map(kind => <button type="button" key={kind} onClick={() => insert(kind)}>
            {t(`scenarios.block_${kind}`)}<Icon name="chevronRight" size={14} /></button>)}
        </div>
      </>}
      {drawer.kind === "addTrigger" && <div className="scenario-palette">
        {(["staff", "ai", "chatballs", "service", "schedule", "api", "scenario"] as const).map(kind => <button type="button" key={kind} onClick={() => addTrigger(kind)}>
          {t(`scenarios.trigger_${kind}`)}<Icon name="chevronRight" size={14} /></button>)}
      </div>}
      {block && <BlockEditor block={block} document={draft.definition} catalog={catalog} timezone={catalog.timezone} scenarioId={draft.id}
        issues={editor.issues.filter(issue => issue.path.startsWith(`${blockPath(draft.definition.steps, block.id)}.`))}
        change={patch => editor.mutate(document => { const found = findBlock(document.steps, block.id); if (found) Object.assign(found, patch); })}
        onInput={(name, schema) => editor.mutate(document => { (document.parameters.properties ??= {})[name] = schema; })} />}
      {trigger && <><TriggerEditor trigger={trigger} access={draft.definition.access} catalog={catalog}
        policies={draft.agentPolicies} onPolicy={(agent, mode) => editor.setDraft(current => current ? { ...current,
          agentPolicies: [...(current.agentPolicies ?? []).filter(row => row.agent !== agent),
            { agent, mode, revision: current.agentPolicies?.find(row => row.agent === agent)?.revision ?? 0 }] } : current)}
        change={patch => editor.mutate(document => { const found = document.triggers.find(t => t.id === trigger.id); if (found) Object.assign(found, patch); })}
        onAccess={access => editor.mutate(document => { document.access = access; })} />
        {trigger.kind === "api" && <ExternalKeyFields value={draft.externalKeys?.find(key => key.trigger === trigger.id)}
          disabled={editor.dirty || editor.saving} rotate={() => editor.rotateKey(trigger.id)} />}
        <button type="button" className="link is-muted" onClick={() => { editor.mutate(document => { document.triggers = document.triggers.filter(t => t.id !== trigger.id); }); close(); }}>{t("scenarios.remove")}</button>
      </>}
      {drawer.kind === "condition" && <ConditionsEditor value={draft.definition.conditions} document={draft.definition} catalog={catalog}
        onChange={conditions => editor.mutate(document => { document.conditions = conditions; })} />}
    </fieldset>
  </Drawer>;
}

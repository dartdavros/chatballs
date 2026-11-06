import { t } from "../../../i18n";
import { SelectField } from "../../../shared/form-controls";
import { valueOptions } from "./bindingOptions";
import { BoundField } from "./BoundField";
import { ConditionsEditor } from "./ConditionsEditor";
import { EntityLinkFields } from "./EntityLinkFields";
import { blockPath, operationFor, operations, schemaField } from "./model";
import { sameReference } from "./referenceModel";
import type { Block, BoundValue, DataSchema, EditorCatalog, Issue, ScenarioDocument } from "./types";
import { WaitEditor } from "./WaitEditor";

export function BlockEditor({ block, document, catalog, timezone, change, onInput, issues = [], scenarioId }: {
  block: Block; document: ScenarioDocument; catalog: EditorCatalog; timezone: string;
  change: (patch: Partial<Block>) => void; onInput: (name: string, schema: DataSchema) => void;
  issues?: Issue[];
  scenarioId?: string;
}) {
  const operation = operationFor(catalog, block);
  const called = catalog.scenarios.find(s => s.id === block.scenario);
  const inputs = block.kind === "call" && called ? schemaField("", called.parameters).fields : operation?.input.fields;
  const lists = valueOptions(document, catalog, block.id).filter(option => option.field.type === "array");
  function input(name: string, value: BoundValue | undefined) {
    const next = { ...block.inputs }; if (value === undefined) delete next[name]; else next[name] = value; change({ inputs: next });
  }
  return <div className="scenario-form">
    {issues.length > 0 && <p className="scenario-field-error" role="alert">{issues[0].message}</p>}
    {block.kind === "action" && <>
      <SelectField label={t("scenarios.connection")} value={block.connection ?? ""} wide
        options={[["", t("scenarios.select")], ["chatballs", t("scenarios.chatballs")], ...catalog.connections.map(c => [String(c.id), c.name] as [string, string])]}
        onChange={connection => change({ connection, target: "", inputs: {} })} />
      <SelectField label={t("scenarios.action")} value={block.target ?? ""} wide
        options={[["", t("scenarios.select")], ...operations(catalog, block.connection ?? "").map(op => [op.key, op.title] as [string, string])]}
        onChange={target => change({ target, inputs: {} })} />
    </>}
    {block.kind === "call" && <>
      <p className="scenario-note">{t("scenarios.child_note")}</p>
      <SelectField label={t("scenarios.title")} value={block.scenario ?? ""} options={[["", t("scenarios.select")], ...catalog.scenarios.filter(s => s.id !== scenarioId).map(s => [s.id, s.name] as [string, string])]}
        onChange={scenario => change({ scenario, inputs: {} })} wide />
    </>}
    {block.target === "chatballs:entity_link.create" ? <EntityLinkFields block={block} document={document} catalog={catalog} change={change} />
      : (block.kind === "action" || block.kind === "call") && (inputs ?? []).map(field => <BoundField key={field.name} field={field} value={block.inputs?.[field.name]}
      issues={issues} path={`${blockPath(document.steps, block.id)}.inputs.${field.name}`}
      connection={block.connection ?? ""} current={block.id} document={document} catalog={catalog} onChange={value => input(field.name, value)} onInput={onInput} />)}
    {block.kind === "if" && <ConditionsEditor value={block.condition ?? { mode: "all", items: [] }} document={document} catalog={catalog} current={block.id}
      onChange={condition => change({ condition })} />}
    {block.kind === "foreach" && <>
      <SelectField label={t("scenarios.list_source")} value={lists.find(option => sameReference(option.binding, block.list))?.key ?? ""}
        options={[["", t("scenarios.select")], ...lists.map(option => [option.key, option.label] as [string, string])]}
        onChange={key => change({ list: lists.find(option => option.key === key)?.binding })} wide />
      <SelectField label={t("scenarios.concurrency")} value={String(block.concurrency ?? 1)}
        options={[["1", t("scenarios.sequential")], ["5", t("scenarios.five")]]} onChange={value => change({ concurrency: Number(value) })} wide />
    </>}
    {["action", "foreach", "parallel"].includes(block.kind) && <SelectField label={t("scenarios.on_error")} value={block.onError ?? "stop"}
      options={[...(block.kind === "parallel" ? [["wait", t("scenarios.wait_others")] as [string, string]] : []), ["stop", t("scenarios.stop")], ["continue", t("scenarios.continue")]]}
      onChange={onError => change({ onError: onError as Block["onError"] })} wide />}
    {block.kind === "try" && <SelectField label={t("scenarios.after_catch")} value={block.after ?? "continue"}
      options={[["continue", t("scenarios.continue")], ["fail", t("scenarios.fail")]]} onChange={after => change({ after: after as Block["after"] })} wide />}
    {block.kind === "wait" && <WaitEditor block={block} catalog={catalog} timezone={timezone} change={change} />}
    {block.kind === "wait" && block.mode === "until" && <BoundField field={schemaField("until", { type: "datetime", title: t("scenarios.type_datetime"), required: true })}
      value={block.until} connection={block.connection ?? ""} current={block.id} document={document} catalog={catalog}
      onChange={value => change({ until: value as Block["until"] })} onInput={onInput} />}
    {block.kind === "wait" && block.mode === "event" && <ConditionsEditor value={block.condition ?? { mode: "all", items: [] }}
      document={{ ...document, triggers: [{ id: block.id, kind: block.connection ? "service" : "chatballs", connection: block.connection, event: block.event }] }}
      catalog={catalog} current={block.id} onChange={condition => change({ condition })} />}
  </div>;
}

import { t } from "../../../i18n";
import { SelectField } from "../../../shared/form-controls";
import { ConstantValue } from "./ConstantValue";
import { conditionKind, sameReference } from "./conditionModel";
import type { ValueOption } from "./bindingOptions";
import type { Condition, EditorCatalog } from "./types";

export function ConditionFields({ condition, catalog, options, change }: {
  condition: Condition; catalog: EditorCatalog; options: ValueOption[]; change: (next: Condition) => void;
}) {
  const kind = conditionKind(condition);
  const sources = options.filter(o => o.binding.source === (kind === "field" ? "context" : kind));
  const selected = sources.find(o => sameReference(o.binding, condition.left));
  if (condition.kind === "context_present") return <SelectField label={t("scenarios.conditions")} value={String(condition.present ?? true)}
    options={[["true", t("scenarios.contact_present")], ["false", t("scenarios.contact_absent")]]} onChange={present => change({ ...condition, present: present === "true" })} wide />;
  if (condition.kind === "tag" || condition.kind === "channel") return <>
    {condition.kind === "tag" && <SelectField label={t("scenarios.tag_scope")} value={condition.scope ?? "conversation"}
      options={[["conversation", t("scenarios.scope_conversation")], ["contact", t("scenarios.scope_contact")]]}
      onChange={scope => change({ ...condition, scope: scope as Condition["scope"] })} wide />}
    <SelectField label={t(condition.kind === "tag" ? "scenarios.tag" : "scenarios.channel")} value={String(condition.kind === "tag" ? condition.tag ?? "" : condition.connection ?? "")}
      options={[["", t("scenarios.select")], ...(condition.kind === "tag" ? catalog.labels : catalog.channels).map(c => [String(c.id), c.name] as [string, string])]}
      onChange={id => change({ ...condition, ...(condition.kind === "tag" ? { tag: Number(id) } : { connection: Number(id) }) })} wide />
    <SelectField label={t("scenarios.conditions")} value={String(condition.present ?? true)} options={condition.kind === "tag"
      ? [["true", t("scenarios.tag_present")], ["false", t("scenarios.tag_absent")]] : [["true", t("scenarios.op_eq")], ["false", t("scenarios.op_ne")]]}
      onChange={present => change({ ...condition, present: present === "true" })} wide />
  </>;
  if (condition.kind === "no_link" || condition.kind === "has_link") {
    const entities = catalog.adapters.find(a => a.key === catalog.connections.find(c => String(c.id) === String(condition.connection))?.adapter)?.entities ?? [];
    return <>
      <SelectField label={t("scenarios.connection")} value={String(condition.connection ?? "")} options={[["", t("scenarios.select")], ...catalog.connections.map(c => [String(c.id), c.name] as [string, string])]}
        onChange={connection => change({ ...condition, connection, entity: "" })} wide />
      <SelectField label={t("scenarios.entity")} value={condition.entity ?? ""} options={[["", t("scenarios.select")], ...entities.map(e => [e.key, e.title] as [string, string])]}
        onChange={entity => change({ ...condition, entity })} wide />
      <SelectField label={t("scenarios.conditions")} value={condition.kind} options={[["no_link", t("scenarios.link_absent")], ["has_link", t("scenarios.link_present")]]}
        onChange={kind => change({ ...condition, kind: kind as Condition["kind"] })} wide />
    </>;
  }
  const ops = ["filled", "empty", "eq", "ne", ...(selected?.field.type === "string" ? ["contains"]
    : ["integer", "number", "date", "datetime"].includes(selected?.field.type ?? "") ? ["gt", "gte", "lt", "lte"] : [])];
  return <>
    <SelectField label={t("scenarios.field")} value={selected?.key ?? ""} options={[["", t("scenarios.select")], ...sources.map(o => [o.key, o.label] as [string, string])]}
      onChange={key => { const left = sources.find(o => o.key === key)?.binding; change({ left, op: left?.aspect ? "eq" : "filled", ...(left?.aspect ? { right: { source: "constant", value: "completed" } } : {}) }); }} wide />
    <SelectField label={t("scenarios.conditions")} value={condition.op ?? "filled"} options={ops.map(op => [op, t(`scenarios.op_${op as "eq" | "ne" | "gt" | "gte" | "lt" | "lte" | "contains" | "empty" | "filled"}`)])}
      onChange={op => change({ ...condition, op, right: { source: "constant", value: selected?.field.options?.[0]?.value ?? "" } })} wide />
    {selected && !["empty", "filled"].includes(condition.op ?? "") && <ConstantValue field={{ ...selected.field, title: t("scenarios.value") }} value={condition.right?.value}
      connection={String(condition.connection ?? "")} catalog={catalog} onChange={value => change({ ...condition, right: { source: "constant", value } })} />}
  </>;
}

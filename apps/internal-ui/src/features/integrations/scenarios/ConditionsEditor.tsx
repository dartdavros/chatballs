import { t } from "../../../i18n";
import { SelectField } from "../../../shared/form-controls";
import { Icon } from "../../../shared/icons";
import { ConditionFields } from "./ConditionFields";
import { conditionKind, conditionOptions, newCondition } from "./conditionModel";
import type { Condition, Conditions, EditorCatalog, ScenarioDocument } from "./types";

export function ConditionsEditor({ value, document, catalog, current = "", onChange }: {
  value: Conditions; document: ScenarioDocument; catalog: EditorCatalog; current?: string; onChange: (next: Conditions) => void;
}) {
  const options = conditionOptions(document, catalog, current);
  const kinds: Array<[string, string]> = [["contact", t("scenarios.contact")], ["tag", t("scenarios.tag")], ["channel", t("scenarios.channel")],
    ["field", t("scenarios.contact_field")], ["linked", t("scenarios.linked_record")],
    ...(["step", "event", "item", "error", "parameter"] as const).filter(source => options.some(o => o.binding.source === source)).map(source => [source, t(`scenarios.source_${source}`)] as [string, string])];
  function change(index: number, condition: Condition) { onChange({ ...value, items: value.items.map((item, i) => i === index ? condition : item) }); }
  return <div className="scenario-form">
    {value.items.length > 1 && <SelectField label={t("scenarios.conditions")} value={value.mode} options={[["all", t("scenarios.all")], ["any", t("scenarios.any")]]}
      onChange={mode => onChange({ ...value, mode: mode as Conditions["mode"] })} wide />}
    {value.items.map((condition, index) => <div className="scenario-condition-form" key={index}>
      <SelectField label={t("scenarios.condition_check")} value={conditionKind(condition)} options={kinds} onChange={kind => change(index, newCondition(kind, options))} wide />
      <ConditionFields condition={condition} catalog={catalog} options={options} change={next => change(index, next)} />
      <button type="button" className="link is-muted" onClick={() => onChange({ ...value, items: value.items.filter((_, i) => i !== index) })}>{t("scenarios.remove")}</button>
    </div>)}
    <button type="button" className="link has-icon" onClick={() => onChange({ ...value, items: [...value.items, newCondition("contact", options)] })}>
      <Icon name="plus" size={14} />{t("scenarios.add_condition")}</button>
  </div>;
}

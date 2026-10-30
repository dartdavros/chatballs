import { t } from "../../../i18n";
import { SelectField } from "../../../shared/form-controls";
import { valueOptions } from "./bindingOptions";
import { findBlock, operationFor } from "./model";
import type { Binding, Block, EditorCatalog, ScenarioDocument } from "./types";

export function EntityLinkFields({ block, document, catalog, change }: {
  block: Block; document: ScenarioDocument; catalog: EditorCatalog; change: (patch: Partial<Block>) => void;
}) {
  const records = valueOptions(document, catalog, block.id).filter(option => {
    if (option.binding.source !== "step" || option.binding.path || option.binding.aspect) return false;
    const producer = findBlock(document.steps, option.binding.step!);
    return producer && operationFor(catalog, producer)?.entityKind;
  });
  const binding = block.inputs?.external_id as Binding | undefined;
  const selected = records.find(option => option.binding.step === binding?.step);
  return <SelectField label={t("scenarios.record")} value={selected?.key ?? ""}
    options={[["", t("scenarios.select")], ...records.map(record => [record.key, record.label] as [string, string])]}
    onChange={key => {
      const record = records.find(option => option.key === key);
      const producer = record && findBlock(document.steps, record.binding.step!);
      const operation = producer && operationFor(catalog, producer);
      if (record && producer && operation) change({ inputs: {
        connection: { source: "constant", value: Number(producer.connection) },
        entity: { source: "constant", value: operation.entityKind },
        external_id: { ...record.binding, ...(record.field.type === "string" ? {} : { transform: "text.stringify@1" }) },
      } });
    }} wide />;
}

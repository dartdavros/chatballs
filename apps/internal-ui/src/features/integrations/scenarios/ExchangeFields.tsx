import { t } from "../../../i18n";
import { SelectField } from "../../../shared/form-controls";
import { ConstantValue } from "./ConstantValue";
import { ExchangeValues } from "./ExchangeValues";
import { mappingAllowed, type ExchangePair } from "./exchangeModel";
import type { EditorCatalog, Mapping, SyncPair } from "./types";

export function ExchangeFields({ descriptor, value, catalog, connection, onChange }: {
  descriptor: ExchangePair; value: SyncPair; catalog: EditorCatalog; connection: number; onChange: (next: SyncPair) => void;
}) {
  function update(left: string, direction: Mapping["direction"], patch: Mapping | null) {
    onChange({ ...value, fields: [...value.fields.filter(f => f.left !== left || f.direction !== direction), ...(patch ? [patch] : [])] });
  }
  const directions: Mapping["direction"][] = value.direction === "both" ? ["forward", "reverse"] : [value.direction];
  return <div className="scenario-form">{directions.map(direction => <div key={direction}>
    <strong>{t(direction === "forward" ? "scenarios.exchange_values_forward" : "scenarios.exchange_values_reverse")}</strong>
    <div className="exchange-map"><div className="exchange-map-row exchange-map-head"><span>{t("scenarios.chatballs")}</span><span /> <span>{t("scenarios.service")}</span></div>
      {(descriptor.left.fields.fields ?? []).filter(field => direction !== "reverse" || descriptor.left.writableFields?.includes(field.name)).map(left => {
        const mapping = value.fields.find(f => f.left === left.name && f.direction === direction);
        const right = descriptor.right.fields.fields?.find(f => f.name === mapping?.right);
        const source = direction === "forward" ? left : right, target = direction === "forward" ? right : left;
        const choices = descriptor.right.fields.fields?.filter(f => mappingAllowed(descriptor, left.name, f.name, direction, catalog)) ?? [];
        const transforms = source && target ? catalog.transforms.filter(t => t.inputTypes.includes(source.type) && (t.outputType === target.type || t.outputType === "any")) : [];
        const transform = transforms.find(t => t.key === mapping?.transform);
        return <div key={left.name}>
          <div className="exchange-map-row"><span>{left.title}</span><span>{direction === "forward" ? "→" : "←"}</span>
            <SelectField label={left.title} value={mapping?.right ?? ""} options={[["", t("scenarios.exchange_no_change")], ...choices.map(f => [f.name, f.title] as [string, string])]}
              onChange={right => update(left.name, direction, right ? { left: left.name, right, direction } : null)} wide />
          </div>
          {mapping && source && target && (source.lookup || source.options) && (target.lookup || target.options) ?
            <ExchangeValues source={source} target={target} connection={connection} value={mapping} onChange={next => update(left.name, direction, next)} />
            : mapping && transforms.length > 0 && <div className="exchange-transform">
              <SelectField label={t("scenarios.transform")} value={mapping.transform ?? ""} options={[["", t("scenarios.no_transform")], ...transforms.map(t => [t.key, t.title] as [string, string])]}
                onChange={key => update(left.name, direction, key ? { ...mapping, transform: key, args: {} } : { left: mapping.left, right: mapping.right, direction })} wide />
              {transform && <ConstantValue field={transform.arguments} value={mapping.args ?? {}} connection={String(connection)} catalog={catalog}
                onChange={args => update(left.name, direction, { ...mapping, args: args as Record<string, unknown> })} />}
            </div>}
        </div>;
      })}
    </div>
  </div>)}</div>;
}

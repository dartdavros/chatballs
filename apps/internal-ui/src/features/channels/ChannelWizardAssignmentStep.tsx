import { SelectField } from "../../shared/form-controls";
import { Button } from "../../shared/ui-controls";
import type { Product } from "../../types";
import { POLICY_FLAGS, POLICY_LABELS, PRESET_LABELS } from "./model";
import type { ChannelPolicy, PolicyPreset } from "./types";

export function ChannelWizardAssignmentStep({
  productId,
  products,
  preset,
  policy,
  busy,
  onProductChange,
  onPresetChange,
  onBack,
  onSubmit,
}: {
  productId: number | null;
  products: Product[];
  preset: PolicyPreset;
  policy: ChannelPolicy;
  busy: boolean;
  onProductChange: (value: number | null) => void;
  onPresetChange: (value: PolicyPreset) => void;
  onBack: () => void;
  onSubmit: () => void;
}) {
  const needsProduct = preset === "SALES" || preset === "SUPPORT";
  return (
    <section className="channel-card-section">
      <header><h3>Назначение</h3></header>
      <div className="channel-wizard-fields">
        <SelectField label="Продукт" value={productId === null ? "" : String(productId)} onChange={(value) => onProductChange(value ? Number(value) : null)} options={[["", "— непродуктовый"], ...products.map((item) => [String(item.id), item.name] as [string, string])]} />
        <SelectField label="Пресет политики" value={preset} onChange={(value) => onPresetChange(value as PolicyPreset)} options={(Object.keys(PRESET_LABELS) as PolicyPreset[]).map((item) => [item, PRESET_LABELS[item]])} />
        {needsProduct && productId === null && <p className="channel-field-hint is-warning">Пресет «{PRESET_LABELS[preset]}» работает только с продуктом — выберите продукт.</p>}
      </div>
      <div className="channel-wizard-policy">
        {POLICY_FLAGS.map((flag) => <span key={flag} className={policy[flag] ? "is-on" : ""}>{POLICY_LABELS[flag].title}</span>)}
      </div>
      <div className="channel-wizard-actions">
        <Button variant="secondary" onClick={onBack}>Назад</Button>
        <Button variant="primary" disabled={busy || (needsProduct && productId === null)} onClick={onSubmit}>Создать канал</Button>
      </div>
    </section>
  );
}

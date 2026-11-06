import { Drawer } from "antd";
import { useState } from "react";
import { t } from "../../../i18n";
import { SelectField } from "../../../shared/form-controls";
import { Segmented } from "../../../shared/ui";
import { Button, IconButton } from "../../../shared/ui-controls";
import { ExchangeFields } from "./ExchangeFields";
import { exchangePairs, makePair, pairKey } from "./exchangeModel";
import type { EditorCatalog, ExchangeSettings, SyncPair } from "./types";

export function ExchangeDrawer({ connection, adapter, catalog, settings, saving, error, onClose, onSave }: {
  connection: { id: number; name: string }; adapter: string; catalog: EditorCatalog; settings: ExchangeSettings;
  saving: boolean; error: string; onClose: () => void; onSave: (value: ExchangeSettings) => Promise<boolean>;
}) {
  const descriptors = exchangePairs(catalog, adapter);
  const [pairs, setPairs] = useState(() => descriptors.map(descriptor => settings.definition.synchronization.find(p => pairKey(p) === descriptor.key) ?? makePair(descriptor, connection.id)));
  const [selected, setSelected] = useState(pairs.find(p => p.enabled)?.id ?? pairs[0]?.id ?? "");
  const pair = pairs.find(p => p.id === selected);
  const descriptor = pair && descriptors.find(d => d.key === pairKey(pair));
  const update = (next: SyncPair) => setPairs(items => items.map(p => p.id === next.id ? next : p));
  const save = async () => { if (await onSave({ revision: settings.revision, definition: { version: 1, synchronization: pairs } })) onClose(); };
  return <Drawer open width={560} closable={false} onClose={() => { if (!saving) onClose(); }} className="exchange-drawer"
    title={<div><small>{connection.name}</small><div>{t("scenarios.exchange_title")}</div></div>}
    extra={<IconButton icon="close" label={t("common.close")} disabled={saving} onClick={onClose} />}
    footer={<div className="exchange-footer"><Button variant="secondary" disabled={saving} onClick={onClose}>{t("scenarios.cancel")}</Button>
      <Button variant="primary" disabled={saving} onClick={() => void save()}>{t(settings.revision ? "scenarios.save" : "scenarios.exchange_save_enable")}</Button></div>}>
    <fieldset className="scenario-form scenario-fieldset" disabled={saving}>
      {error && <p className="scenario-banner" role="alert">{error}</p>}
      <section className="scenario-form"><div><strong>{t("scenarios.exchange_records")}</strong><p className="scenario-note">{t("scenarios.exchange_linked")}</p></div>
        {pairs.map(p => { const d = descriptors.find(d => d.key === pairKey(p))!; return <div className="exchange-pair" key={p.id}>
          <label><input type="checkbox" checked={p.enabled} onChange={e => { update({ ...p, enabled: e.target.checked }); setSelected(p.id); }} />
            <strong>{d.left.title} ↔ {d.right.title}</strong></label>
          {p.enabled && <Segmented value={p.direction} setValue={direction => update({ ...p, direction })}
            disabledKeys={(["forward", "reverse", "both"] as const).filter(direction => !d.right.synchronization?.directions.includes(direction))}
            items={(["forward", "reverse", "both"] as const).map(direction => [direction, t(`scenarios.${direction}`)])} />}
        </div>; })}
      </section>
      {descriptor?.right.synchronization?.directions.length === 1 && <p className="scenario-note">{t("scenarios.exchange_read_only")}</p>}
      <section className="scenario-form"><div><strong>{t("scenarios.exchange_fields")}</strong><p className="scenario-note">{t("scenarios.exchange_hint")}</p></div>
        {pairs.length > 1 && <Segmented value={selected} setValue={setSelected} items={pairs.map(p => [p.id, descriptors.find(d => d.key === pairKey(p))!.right.title])} />}
        {pair && descriptor && <ExchangeFields key={pair.id} descriptor={descriptor} value={pair} connection={connection.id} catalog={catalog} onChange={update} />}
      </section>
      {pair && <section className="scenario-form"><strong>{t("scenarios.exchange_conflict")}</strong>
        {(["latest", "left", "right", "manual"] as const).map(choice => <label className="exchange-conflict" key={choice}>
          <input type="radio" name="exchange-conflict" checked={choice === "manual" ? pair.conflict === "manual" : pair.conflict !== "manual" && pair.sourceOfTruth === choice}
            onChange={() => update({ ...pair, sourceOfTruth: choice === "manual" ? "latest" : choice, conflict: choice === "manual" ? "manual" : choice === "latest" ? "latest" : "source" })} />
          <span>{t(choice === "manual" ? "scenarios.exchange_manual" : choice === "left" ? "scenarios.exchange_native_wins" : choice === "right" ? "scenarios.exchange_service_wins" : "scenarios.latest")}</span>
        </label>)}
        <SelectField label={t("scenarios.deletion")} value={pair.deletion} options={(descriptor?.right.synchronization?.deletion ?? ["unlink", "keep"]).map(v => [v, t(`scenarios.${v}`)])}
          onChange={deletion => update({ ...pair, deletion: deletion as SyncPair["deletion"] })} wide />
      </section>}
    </fieldset>
  </Drawer>;
}

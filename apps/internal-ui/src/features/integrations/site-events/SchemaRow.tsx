import { useState } from "react";
import { Dropdown } from "antd";
import { t } from "../../../i18n";
import { FormField, SelectField, SwitchButton } from "../../../shared/form-controls";
import { Icon } from "../../../shared/icons";
import type { DraftField } from "./model";

export function SchemaRow({ value, onChange, onRemove, disabled }: {
  value: DraftField; onChange: (next: DraftField) => void; onRemove: () => void; disabled: boolean;
}) {
  const [open, setOpen] = useState(false);
  const set = (patch: Partial<DraftField>) => onChange({ ...value, ...patch });
  return <tr className="ev-schema-row">
    <td className="ev-cell-unlabelled"><FormField label={t("site_events.field")} mono value={value.name} disabled={disabled} onChange={(name) => set({ name })} /></td>
    <td className="ev-cell-unlabelled"><SelectField label={t("site_events.type")} value={value.type} disabled={disabled}
      onChange={(type) => set({ type: type as DraftField["type"] })}
      options={[["string", t("site_events.string")], ["number", t("site_events.number")], ["boolean", t("site_events.boolean")]]} /></td>
    <td className="ev-schema-limits">{value.type === "string"
      ? <FormField label={t("site_events.max_length")} type="number" value={value.maxLength} disabled={disabled} onChange={(maxLength) => set({ maxLength })} />
      : value.type === "number" ? <div className="ev-range">
        <FormField label={t("site_events.minimum")} type="number" value={value.minimum} disabled={disabled} onChange={(minimum) => set({ minimum })} />
        <FormField label={t("site_events.maximum")} type="number" value={value.maximum} disabled={disabled} onChange={(maximum) => set({ maximum })} />
      </div> : <span aria-hidden="true">—</span>}</td>
    <td><SwitchButton label={t("site_events.required")} checked={value.required} disabled={disabled} className="ui-switch is-compact" onClick={() => set({ required: !value.required })} /></td>
    <td><Dropdown open={open} onOpenChange={setOpen} trigger={["click"]} overlayClassName="app-dropdown" menu={{ items: [
      { key: "remove", label: <button type="button" className="warning" onClick={() => { setOpen(false); onRemove(); }}><Icon name="trash" size={15} />{t("site_events.remove_field")}</button> },
    ] }}><button type="button" className="row-menu-button" disabled={disabled} aria-label={t("site_events.actions")}><Icon name="more" /></button></Dropdown></td>
  </tr>;
}

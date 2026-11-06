import { t } from "../../../i18n";
import { SelectField, SwitchButton } from "../../../shared/form-controls";
import type { Access, EditorCatalog } from "./types";

export function ToggleField({ label, checked, onChange }: { label: string; checked: boolean; onChange: (next: boolean) => void }) {
  return <div className="scenario-toggle"><span>{label}</span><SwitchButton className="ui-switch is-compact" label={label} checked={checked} onClick={() => onChange(!checked)} /></div>;
}
export function AccessFields({ value, catalog, onChange }: { value: Access; catalog: EditorCatalog; onChange: (next: Access) => void }) {
  return <div className="scenario-form">
    <SelectField label={t("scenarios.scope")} value={value.scope} options={(["conversation", "contact", "organization"] as const).map(scope => [scope, t(`scenarios.scope_${scope}`)])}
      onChange={scope => onChange({ ...value, scope: scope as Access["scope"] })} wide />
    <div className="scenario-form"><strong>{t("scenarios.available_to")}</strong>
      <ToggleField label={t("scenarios.all_staff")} checked={catalog.staff.length > 0 && catalog.staff.every(employee => value.staff.includes(employee.id))}
        onChange={checked => onChange({ ...value, groups: [], staff: checked ? catalog.staff.map(employee => employee.id) : [] })} />
      {catalog.groups.map(group => <ToggleField key={group.id} label={group.name} checked={value.groups.includes(group.id)}
        onChange={checked => onChange({ ...value, groups: checked ? [...value.groups, group.id] : value.groups.filter(id => id !== group.id) })} />)}
      {catalog.staff.map(employee => <ToggleField key={employee.id} label={employee.name} checked={value.staff.includes(employee.id)}
        onChange={checked => onChange({ ...value, staff: checked ? [...value.staff, employee.id] : value.staff.filter(id => id !== employee.id) })} />)}
    </div>
    <ToggleField label={t("scenarios.delegated")} checked={value.delegated} onChange={delegated => onChange({ ...value, delegated })} />
    <SelectField label={t("scenarios.confirm")} value={value.confirm} options={(["effects", "always"] as const).map(mode => [mode, t(`scenarios.confirm_${mode}`)])}
      onChange={confirm => onChange({ ...value, confirm: confirm as Access["confirm"] })} wide />
  </div>;
}

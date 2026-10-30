import { useState } from "react";
import { t } from "../../../i18n";
import { FormField, SelectField } from "../../../shared/form-controls";

export function WaitDuration({ seconds, onChange }: { seconds: number; onChange: (seconds: number) => void }) {
  const [unit, setUnit] = useState(seconds % 86400 === 0 ? 86400 : seconds % 3600 === 0 ? 3600 : 60);
  return <div className="scenario-form-pair">
    <FormField label={t("scenarios.duration_after")} type="number" value={String(seconds / unit)} onChange={value => onChange(Number(value) * unit)} wide />
    <SelectField label={t("scenarios.duration_unit")} value={String(unit)}
      options={[["60", t("scenarios.unit_minutes")], ["3600", t("scenarios.unit_hours")], ["86400", t("scenarios.unit_days")]]}
      onChange={value => { const next = Number(value); setUnit(next); onChange(seconds / unit * next); }} wide />
  </div>;
}

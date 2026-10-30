import { t } from "../../../i18n";
import { FormField, SelectField } from "../../../shared/form-controls";
import { ToggleField } from "./AccessFields";
import type { Trigger } from "./types";

export function ScheduleFields({ trigger, timezone, change }: { trigger: Trigger; timezone: string; change: (patch: Partial<Trigger>) => void }) {
  return <>
    <SelectField label={t("scenarios.frequency")} value={trigger.frequency ?? "daily"}
      options={(["daily", "weekdays", "days", "monthly"] as const).map(frequency => [frequency, t(`scenarios.${frequency}`)])}
      onChange={frequency => change({ frequency: frequency as Trigger["frequency"], ...(frequency === "days" ? { days: [0] } : {}),
        ...(frequency === "monthly" ? { dayOfMonth: trigger.dayOfMonth ?? 1 } : {}) })} wide />
    {trigger.frequency === "days" && <div>{Array.from({ length: 7 }, (_, index) => {
      return <ToggleField key={index} label={t(`scenarios.weekday_${index as 0 | 1 | 2 | 3 | 4 | 5 | 6}`)} checked={trigger.days?.includes(index) ?? false}
        onChange={checked => change({ days: checked ? [...(trigger.days ?? []), index] : (trigger.days ?? []).filter(day => day !== index) })} />;
    })}</div>}
    {trigger.frequency === "monthly" && <SelectField label={t("scenarios.day_of_month")} value={String(trigger.dayOfMonth ?? 1)}
      options={[...Array.from({ length: 28 }, (_, index) => [String(index + 1), String(index + 1)] as [string, string]), ["last", t("scenarios.last_day")]]}
      onChange={day => change({ dayOfMonth: day === "last" ? "last" : Number(day) })} wide />}
    <FormField label={t("scenarios.time")} type="time" value={trigger.time ?? "09:00"} onChange={time => change({ time })} wide />
    <small className="scenario-note">{timezone}</small>
    <SelectField label={t("scenarios.misfire")} value={trigger.misfire ?? "once"} options={[["once", t("scenarios.misfire_once")], ["skip", t("scenarios.misfire_skip")]]}
      onChange={misfire => change({ misfire: misfire as Trigger["misfire"] })} wide />
  </>;
}

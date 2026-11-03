import { t } from "../../../i18n";
import { FormField, SelectField } from "../../../shared/form-controls";
import type { Block, EditorCatalog } from "./types";
import { WaitDuration } from "./WaitDuration";

export function WaitEditor({ block, catalog, timezone, change }: {
  block: Block; catalog: EditorCatalog; timezone: string; change: (patch: Partial<Block>) => void;
}) {
  const connection = catalog.connections.find(c => String(c.id) === block.connection);
  const adapter = catalog.adapters.find(a => a.key === connection?.adapter);
  return <>
    <SelectField label={t("scenarios.wait_for")} value={block.mode ?? "reply"}
      options={(["reply", "duration", "clock", "until", "confirmation", "event"] as const).map(mode => [mode, t(`scenarios.wait_${mode}`)])}
      onChange={mode => change({ mode: mode as Block["mode"], ...(mode === "clock" ? { day: "next", time: "09:00", timezone } : {}),
        ...(mode === "duration" ? { duration: block.duration ?? 3600 } : {}), ...(mode === "event" ? { condition: block.condition ?? { mode: "all", items: [] } } : {}) })} wide />
    {block.mode === "duration" && <WaitDuration key={block.id} seconds={block.duration ?? 3600} onChange={duration => change({ duration })} />}
    {block.mode === "clock" && <>
      <SelectField label={t("scenarios.day")} value={block.day ?? "next"} options={(["next", "work", "date"] as const).map(day => [day, t(`scenarios.day_${day}`)])}
        onChange={day => change({ day: day as Block["day"] })} wide />
      {block.day === "date" && <FormField label={t("scenarios.date")} type="date" value={block.date ?? ""} onChange={date => change({ date })} wide />}
      <FormField label={t("scenarios.time")} type="time" value={block.time ?? "09:00"} onChange={time => change({ time })} wide />
      <small className="scenario-note">{block.timezone ?? timezone}</small>
    </>}
    {block.mode === "event" && <>
      <SelectField label={t("scenarios.connection")} value={block.connection ?? ""} options={[["", t("scenarios.chatballs")], ...catalog.connections.map(c => [String(c.id), c.name] as [string, string])]}
        onChange={connection => change({ connection, event: "", condition: { mode: "all", items: [] } })} wide />
      <SelectField label={t("scenarios.event")} value={block.event ?? ""} options={[["", t("scenarios.select")], ...(block.connection ? adapter?.events ?? [] : catalog.events).map(event => [event.key, event.title] as [string, string])]}
        onChange={event => change({ event })} wide />
    </>}
    {block.mode === "confirmation" && <><SelectField label={t("scenarios.approver")} value={block.approver ?? "initiator"}
      options={[["initiator", t("scenarios.approver_initiator")], ...catalog.staff.map(s => [String(s.id), s.name] as [string, string])]}
      onChange={approver => change({ approver })} wide />
      <FormField label={t("runs.confirmation_text")} value={block.message ?? ""} onChange={message => change({ message })} wide /></>}
    {["reply", "confirmation", "event"].includes(block.mode ?? "reply") && <>
      <SelectField label={t("scenarios.timeout")} value={String(block.timeout ?? 86400)}
        options={[["3600", t("scenarios.timeout_hour")], ["86400", t("scenarios.timeout_day")], ["259200", t("scenarios.timeout_three_days")]]}
        onChange={value => change({ timeout: Number(value) })} wide />
      <SelectField label={t("scenarios.on_timeout")} value={block.onTimeout ?? "continue"}
        options={[["continue", t("scenarios.continue")], ["end", t("scenarios.end")]]} onChange={onTimeout => change({ onTimeout: onTimeout as Block["onTimeout"] })} wide />
    </>}
  </>;
}

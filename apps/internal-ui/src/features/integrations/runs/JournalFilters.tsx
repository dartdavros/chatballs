import { useState } from "react";
import { t } from "../../../i18n";
import { FilterDropdown, SearchInput } from "../../../shared/ui-controls";
import { Segmented } from "../../../shared/ui";
import type { RunPage } from "./types";

export type JournalQuery = { q: string; connection: string; initiator: string; period: string; group: string };
export const emptyJournalQuery: JournalQuery = { q: "", connection: "", initiator: "", period: "30", group: "" };

export function JournalFilters({ value, change, filters }: { value: JournalQuery; change: (value: JournalQuery) => void; filters?: RunPage["filters"] }) {
  const [open, setOpen] = useState("");
  const definitions = [
    { key: "connection" as const, caption: t("runs.connection"), options: (filters?.connections ?? []).map(row => ({ value: String(row.id), label: row.name })) },
    { key: "initiator" as const, caption: t("runs.initiator"), options: (filters?.initiators ?? []).map(row => ({ value: String(row.initiator_id), label: row.initiator__user__full_name })) },
    { key: "period" as const, caption: t("runs.period"), options: [{ value: "30", label: t("runs.last30") }, { value: "", label: t("runs.all_time") }] },
  ];
  return <div className="run-filters"><SearchInput placeholder={t("runs.search")} value={value.q} onChange={q => change({ ...value, q })} />
    {definitions.map(filter => { const options = filter.key === "period" ? filter.options : [{ value: "", label: t("runs.all") }, ...filter.options];
      return <FilterDropdown key={filter.key} label={`${filter.caption}: ${options.find(option => option.value === value[filter.key])?.label ?? t("runs.all")}`}
        selected={value[filter.key] ? [value[filter.key]] : []} options={options} open={open === filter.key} onOpenChange={show => setOpen(show ? filter.key : "")}
        onSelect={next => change({ ...value, [filter.key]: next })} />;
    })}<span className="run-filter-spacer" /><Segmented value={value.group} setValue={group => change({ ...value, group })}
      items={[["", t("runs.all")], ["attention", t("runs.attention")], ["active", t("runs.active")], ["finished", t("runs.finished")]]} />
  </div>;
}

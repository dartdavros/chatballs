import { t } from "../../../i18n";
import { UnderlineTabs } from "../../../shared/ui-controls";

export function RunTabs({ journal, onChange }: { journal: boolean; onChange: (journal: boolean) => void }) {
  return <UnderlineTabs className="integrations-tabs" value={journal ? "runs" : "scenarios"} onChange={value => onChange(value === "runs")}
    items={[{ key: "scenarios", label: t("scenarios.title") }, { key: "runs", label: t("runs.title") }]} />;
}

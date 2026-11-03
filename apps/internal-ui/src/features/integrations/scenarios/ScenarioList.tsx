import { t } from "../../../i18n";
import { Icon } from "../../../shared/icons";
import { StatusPill } from "../../../shared/ui";
import { Button } from "../../../shared/ui-controls";
import type { EditorCatalog, Scenario, TriggerKind } from "./types";

import { RunTabs } from "../runs/RunTabs";

export function ScenarioList({ rows, catalog, open, openJournal }: { rows: Scenario[]; catalog: EditorCatalog; open: (id: string) => void; openJournal: () => void }) {
  return <div className="scenarios-list">
    <header className="settings-head">
      <div><h2>{t("scenarios.title")}</h2><p>{t("scenarios.lead")}</p></div>
      <Button variant="primary" icon="plus" onClick={() => open("new")}>{t("scenarios.create")}</Button>
    </header>
    <RunTabs journal={false} onChange={journal => { if (journal) openJournal(); }} />
    <div className="scenario-table">
      <div className="scenario-table-row is-head"><span>{t("scenarios.title")}</span><span>{t("scenarios.launch")}</span>
        <span>{t("scenarios.connections")}</span><span>{t("scenarios.state")}</span><span /></div>
      {rows.map(row => {
        const connections = catalog.connections.filter(c => row.connections.includes(c.id));
        const paused = row.enabled && connections.some(c => !c.isActive || c.status === "lost");
        return <div className="scenario-table-row" key={row.id}>
          <div><button type="button" className="link is-strong" onClick={() => open(row.id)}>{row.name}</button>
            <small>{t(row.origin.key ? "scenarios.origin_preset" : "scenarios.origin_custom")}</small></div>
          <span>{(row.triggers ?? []).map((kind: TriggerKind) => t(`scenarios.trigger_${kind}`)).join(", ")}</span>
          <span>{connections.map(c => c.name).join(", ")}</span>
          <span title={row.automationError}><StatusPill status={row.automationError ? "error" : paused ? "pending" : row.enabled ? "healthy" : "draft"}
            label={t(paused || row.automationError ? "scenarios.paused" : row.enabled ? "scenarios.on" : "scenarios.off")} /></span>
          <button type="button" className="row-menu-button" aria-label={row.name} onClick={() => open(row.id)}><Icon name="chevronRight" size={16} /></button>
        </div>;
      })}
    </div>
    <p className="scenario-note">{t("scenarios.presets_note")}</p>
  </div>;
}

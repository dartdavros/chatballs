import { useState } from "react";
import { t } from "../../../i18n";
import { pathFromRoute, routeFromPath } from "../../../router";
import { requestNavigation } from "../../../shared/navigationGuard";
import { RunDetail } from "./RunDetail";
import { RunJournal } from "./RunJournal";
import { RunTabs } from "./RunTabs";
import "./runs.css";

export function RunsWorkspace({ onScenarios }: { onScenarios: () => void }) {
  const [selected, setSelected] = useState<string | null>(new URLSearchParams(location.search).get("run"));
  const open = (id: string | null) => {
    const url = new URL(location.href);
    if (id) url.searchParams.set("run", id); else url.searchParams.delete("run");
    history.replaceState(history.state, "", url); setSelected(id);
  };
  if (selected) return <RunDetail key={selected} id={selected} onBack={() => open(null)} onRepeated={open} />;
  return <div className="runs-workspace"><header className="settings-head"><div><h2>{t("scenarios.title")}</h2><p>{t("scenarios.lead")}</p></div></header>
    <RunTabs journal onChange={journal => { if (!journal) onScenarios(); }} />
    <RunJournal open={open} openRetention={() => requestNavigation(() => {
      location.assign(pathFromRoute("settings", "organization", routeFromPath(location.pathname).organizationPublicId));
    })} />
  </div>;
}

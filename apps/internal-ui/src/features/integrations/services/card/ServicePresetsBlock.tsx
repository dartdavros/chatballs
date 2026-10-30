import { useEffect, useState } from "react";
import { t } from "../../../../i18n";
import { Button } from "../../../../shared/ui-controls";
import { copyPreset, listScenarios } from "../../scenarios/api";
import { retainPresetKeys } from "../../scenarios/presetTransfer";
import type { Scenario } from "../../scenarios/types";
import type { ServiceAdapter } from "../types";

export function ServicePresetsBlock({ adapter, connectionId, onOpen }: { adapter: ServiceAdapter; connectionId: number; onOpen: (id: string) => void }) {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    setLoading(true); setFailed(false);
    let active = true;
    listScenarios(connectionId).then(rows => { if (active) setScenarios(rows); }).catch(() => { if (active) setFailed(true); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [connectionId]);
  async function openPreset(key: string) {
    setBusy(true);
    try {
      const current = failed ? await listScenarios(connectionId) : scenarios;
      setScenarios(current); setFailed(false);
      const existing = current.find(scenario => scenario.origin.adapter === adapter.key && scenario.origin.key === key);
      if (existing) { onOpen(existing.id); return; }
      const scenario = await copyPreset(connectionId, key); retainPresetKeys(scenario); onOpen(scenario.id);
    }
    catch { setFailed(true); } finally { setBusy(false); }
  }
  return <section className="service-card-block service-presets">
      <h3>{t("services.scenarios_title")}</h3>
      <p className="service-card-lead">{t("services.scenarios_lead", { service: adapter.title })}</p>
      {failed && <p role="alert">{t("services.request_failed")}</p>}
      {adapter.presets.map((preset) => {
        const existing = scenarios.find(scenario => scenario.origin.adapter === adapter.key && scenario.origin.key === preset.key);
        return <div className="service-preset" key={preset.key}>
          <div>
            <div className="service-preset-name"><strong>{preset.title}</strong><span>{t("services.preset_tag")}</span></div>
            <p>{preset.purpose}</p>
          </div>
          <span className="service-preset-state">{t(existing?.enabled ? "scenarios.on" : "services.preset_not_set")}</span>
          <Button variant="secondary" disabled={loading || busy} onClick={() => void openPreset(preset.key)}>{t(existing ? "common.edit" : "scenarios.configure")}</Button>
        </div>;
      })}
      <button type="button" className="link" onClick={() => onOpen("new")}>{t("scenarios.create")}</button>
    </section>;
}

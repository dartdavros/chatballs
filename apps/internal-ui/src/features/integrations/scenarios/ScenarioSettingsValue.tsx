import { useEffect, useRef, useState, type Dispatch, type SetStateAction } from "react";
import { t } from "../../../i18n";
import { EmptyState, LoadingState } from "../../../shared/ui";
import type { ControlProps } from "../services/connect/fieldControls";
import { fetchCatalog } from "./api";
import { emptyDocument } from "./model";
import { ScenarioDrawer } from "./ScenarioDrawer";
import { ScenarioSections } from "./ScenarioSections";
import type { Drawer, EditorCatalog, Scenario, ScenarioDocument } from "./types";
import "./scenarios.css";

// The same authored editor composes a value. Saving, URL navigation and key
// issuance remain responsibilities of the surrounding product workflow.
export function ScenarioSettingsValue({ field, value, disabled, onChange }: ControlProps) {
  const [catalog, setCatalog] = useState<EditorCatalog | null>(null);
  const [error, setError] = useState("");
  const [drawer, setDrawer] = useState<Drawer | null>(null);
  const [generation, setGeneration] = useState(0);
  const latest = useRef<Scenario | null>(null);
  useEffect(() => {
    let active = true;
    setCatalog(null); setError("");
    void fetchCatalog().then(result => { if (active) setCatalog(result); })
      .catch(() => { if (active) setError(t("scenarios.load_failed")); });
    return () => { active = false; };
  }, [generation]);
  const settings = value && typeof value === "object" && !Array.isArray(value)
    ? value as { definition?: ScenarioDocument; agentPolicies?: Scenario["agentPolicies"] } : {};
  const definition = settings.definition ?? emptyDocument();
  if (!Array.isArray(definition.steps) || !Array.isArray(definition.triggers)
    || !Array.isArray(definition.conditions?.items) || !definition.access || !definition.parameters) {
    return <EmptyState title={t("scenarios.control_unavailable")} />;
  }
  const draft: Scenario = { id: "", name: "", revision: 0, enabled: false, definition,
    origin: { adapter: "", key: "", version: null }, connections: [], updatedAt: "", agentPolicies: settings.agentPolicies };
  latest.current = draft;
  const setDraft: Dispatch<SetStateAction<Scenario | null>> = update => {
    const next = typeof update === "function" ? update(latest.current) : update;
    latest.current = next;
    if (next) onChange({ definition: next.definition, agentPolicies: next.agentPolicies ?? [] });
  };
  const editor = { draft, catalog, drawer, setDrawer, error, conflict: false, issues: [], saving: disabled, dirty: true,
    setDraft, hideKeys: () => {}, rotateKey: async () => {},
    reload: async () => { setGeneration(current => current + 1); },
    mutate: (change: (document: ScenarioDocument) => void) => {
      const next = structuredClone(latest.current!); change(next.definition); setDraft(next);
    } };
  return <fieldset className="scenario-fieldset" disabled={disabled} aria-label={field.title}>
    {error ? <EmptyState title={error} /> : !catalog ? <LoadingState />
      : <><ScenarioSections editor={editor} /><ScenarioDrawer editor={editor} /></>}
  </fieldset>;
}

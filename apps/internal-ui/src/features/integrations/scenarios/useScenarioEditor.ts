import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../../../api/client";
import { t } from "../../../i18n";
import { registerNavigationGuard, releaseNavigationGuard } from "../../../shared/navigationGuard";
import * as api from "./api";
import { emptyDocument } from "./model";
import { takePresetKeys } from "./presetTransfer";
import { unavailableScenarioControl } from "./controlModel";
import { pruneInputs } from "./inputParameters";
import { scheduleScenarioValidation } from "./scenarioValidation";
import { scenarioSnapshot, validCategoryPath } from "./categoryPath";
import type { Drawer, EditorCatalog, Issue, Scenario, ScenarioDocument } from "./types";

function updateScenarioUrl(id: string | null) {
  const url = new URL(location.href);
  if (id) url.searchParams.set("scenario", id); else url.searchParams.delete("scenario");
  history.replaceState(history.state, "", url);
}

export function useScenarioEditor(initial?: string) {
  const [selected, setSelected] = useState<string | null>(initial ?? new URLSearchParams(location.search).get("scenario"));
  const [catalog, setCatalog] = useState<EditorCatalog | null>(null);
  const [rows, setRows] = useState<Scenario[]>([]);
  const [draft, setDraft] = useState<Scenario | null>(null);
  const [saved, setSaved] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [conflict, setConflict] = useState(false);
  const [issues, setIssues] = useState<Issue[]>([]);
  const [validationError, setValidationError] = useState("");
  const [drawer, setDrawer] = useState<Drawer | null>(null);
  const [pendingLeave, setPendingLeave] = useState<(() => void) | null>(null);
  const generation = useRef(0);
  const loadedSelection = useRef<string | null | undefined>(undefined);
  const snapshot = draft ? scenarioSnapshot(draft) : "";
  const dirty = snapshot !== saved;
  const definitionSnapshot = draft ? JSON.stringify(draft.definition) : "";
  const validateDraft = !loading && !saving;

  useEffect(() => {
    setValidationError("");
    if (!validateDraft || !definitionSnapshot) return;
    return scheduleScenarioValidation(
      signal => api.checkScenario(JSON.parse(definitionSnapshot) as ScenarioDocument, signal),
      setIssues,
      () => setValidationError(t("scenarios.request_failed")),
    );
  }, [definitionSnapshot, validateDraft, selected]);

  const load = useCallback(async (target = selected) => {
    const token = ++generation.current;
    setLoading(true); setError(""); setConflict(false); setDrawer(null);
    try {
      const [metadata, list, scenario] = await Promise.all([api.fetchCatalog(), api.listScenarios(),
        target && target !== "new" ? api.fetchScenario(target) : Promise.resolve(null)]);
      if (generation.current !== token) return;
      if (scenario) {
        const keys = takePresetKeys(scenario.id);
        if (keys) scenario.externalKeys = scenario.externalKeys?.map(key => keys.find(fresh => fresh.id === key.id) ?? key);
      }
      loadedSelection.current = target;
      setCatalog(metadata); setRows(list);
      const next = scenario ?? (target === "new" ? { id: "", name: t("scenarios.new_name"), revision: 0,
        enabled: false, categoryPath: [], definition: emptyDocument(), origin: { adapter: "", key: "", version: null }, connections: [], updatedAt: "" } : null);
      setDraft(next); setSaved(next && next.id ? scenarioSnapshot(next) : "");
      setIssues(next?.issues ?? []);
    } catch { if (generation.current === token) setError(t("scenarios.load_failed")); }
    finally { if (generation.current === token) setLoading(false); }
  }, [selected]);
  useEffect(() => { if (loadedSelection.current !== selected) void load(); return () => { generation.current++; }; }, [load, selected]);
  useEffect(() => {
    if (!dirty || !draft) return;
    const unregister = registerNavigationGuard(proceed => setPendingLeave(() => proceed));
    const beforeUnload = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", beforeUnload);
    return () => { unregister(); window.removeEventListener("beforeunload", beforeUnload); };
  }, [dirty, Boolean(draft)]);

  function open(id: string | null) {
    const proceed = () => {
      releaseNavigationGuard(); loadedSelection.current = undefined; setSelected(id); setDraft(null); setSaved(""); setPendingLeave(null);
      updateScenarioUrl(id);
    };
    if (dirty && draft) setPendingLeave(() => proceed); else proceed();
  }
  function mutate(change: (document: ScenarioDocument) => void) {
    setDraft(current => {
      if (!current) return current;
      const next = structuredClone(current); change(next.definition); return next;
    });
  }
  function failure(caught: unknown) {
    if (caught instanceof ApiError) {
      const body = caught.payload as { detail?: string; issues?: Issue[]; errors?: Record<string, string[]> } | null;
      if (caught.status === 409) setConflict(true);
      if (body?.issues) setIssues(body.issues);
      setError(body?.issues ? "" : body?.detail ?? Object.values(body?.errors ?? {}).flat()[0] ?? t("scenarios.request_failed"));
    } else setError(t("scenarios.request_failed"));
  }
  async function save(enabled = draft?.enabled ?? false): Promise<boolean> {
    if (!draft || saving) return false;
    if (!validCategoryPath(draft.categoryPath ?? [])) { setError(t("scenarios.category_invalid")); return false; }
    if (catalog && unavailableScenarioControl(draft.definition, catalog)) { setError(t("scenarios.control_unavailable")); return false; }
    setSaving(true); setError("");
    try {
      const definition = structuredClone(draft.definition); pruneInputs(definition);
      const result = await api.saveScenario({ name: draft.name, definition, enabled,
        agentPolicies: draft.agentPolicies, categoryPath: draft.categoryPath ?? [],
        ...(draft.id ? { id: draft.id, revision: draft.revision } : {}) });
      setDraft(result); setIssues(result.issues ?? []);
      loadedSelection.current = result.id; setSelected(result.id);
      setSaved(scenarioSnapshot(result));
      setRows(items => [...items.filter(item => item.id !== result.id), result]);
      updateScenarioUrl(result.id);
      return true;
    } catch (caught) { failure(caught); return false; }
    finally { setSaving(false); }
  }
  async function check() {
    if (!draft) return;
    setSaving(true); setError("");
    try { const result = await api.checkScenario(draft.definition); setIssues(result.issues); }
    catch (caught) { failure(caught); } finally { setSaving(false); }
  }
  async function copy() {
    if (!draft?.id) return;
    setSaving(true);
    try {
      const result = await api.copyScenario(draft.id, draft.name);
      setDraft(result); setSaved(scenarioSnapshot(result));
      loadedSelection.current = result.id; setSelected(result.id);
      setIssues(result.issues ?? []); setRows(items => [...items, result]); releaseNavigationGuard();
      updateScenarioUrl(result.id);
    } catch (caught) { failure(caught); } finally { setSaving(false); }
  }
  async function remove() {
    if (!draft?.id) return false;
    setSaving(true);
    try { await api.deleteScenario(draft.id, draft.revision); setDraft(null); setSaved("");
      loadedSelection.current = undefined; setSelected(null); updateScenarioUrl(null); releaseNavigationGuard(); return true; }
    catch (caught) { failure(caught); return false; } finally { setSaving(false); }
  }
  return { catalog, rows, draft, setDraft, loading, saving, error: error || validationError, conflict, issues, drawer, setDrawer, dirty,
    pendingLeave, setPendingLeave, open, mutate, save, check, copy, remove, reload: () => load(draft?.id || selected),
    hideKeys: () => setDraft(current => current ? { ...current, externalKeys: current.externalKeys?.map(({ key: _key, ...metadata }) => metadata) } : current),
    rotateKey: async (trigger: string) => {
      if (!draft?.id || dirty || saving) return;
      setSaving(true); setError("");
      try { const key = await api.rotateExternalKey(draft.id, trigger, draft.revision);
        setDraft(current => current ? { ...current, externalKeys: [...(current.externalKeys ?? []).filter(item => item.trigger !== trigger), key] } : current);
      } catch (caught) { failure(caught); } finally { setSaving(false); }
    } };
}
export type ScenarioEditorState = ReturnType<typeof useScenarioEditor>;

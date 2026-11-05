import { useEffect, useState } from "react";
import { api } from "../../../api/client";
import { t } from "../../../i18n";
import type { Integration } from "../model";
import { listScenarios } from "../scenarios/api";
import type { Scenario } from "../scenarios/types";
import { draftOf, validatedRule, type DraftRule } from "./model";

export function useRuleEditor(integration: Integration, onSaved: (next: Integration) => void) {
  const [draft, setDraft] = useState(() => draftOf(integration.config.siteEvent));
  const [catalog, setCatalog] = useState<Scenario[]>([]);
  const [catalogStatus, setCatalogStatus] = useState<"loading" | "ready" | "error" | "empty">("loading");
  const [busy, setBusy] = useState(false), [submitted, setSubmitted] = useState(false), [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  function loadCatalog() {
    setCatalogStatus("loading");
    void listScenarios().then((items) => {
      const eligible = items.filter((row) => row.enabled && (row.accessScope === "conversation" || row.accessScope === "contact")
        && row.nativeEvents?.includes("webchat.site_event"));
      setCatalog(eligible); setCatalogStatus(eligible.length ? "ready" : "empty");
    }).catch(() => setCatalogStatus("error"));
  }
  useEffect(loadCatalog, [integration.id]);
  function change(next: DraftRule) { setDraft(next); setSaved(false); setError(""); }
  const value = validatedRule(draft);
  const valid = Boolean(value && catalog.some((row) => row.id === value.scenario));
  async function save() {
    setSubmitted(true);
    if (!valid || !value || busy) return;
    setBusy(true); setError("");
    try {
      const response = await api<{ integration: Integration }>(`/api/v1/integrations/${integration.id}/`, {
        method: "PATCH", body: JSON.stringify({ config: { ...integration.config, siteEvent: value } }),
      });
      setDraft(draftOf(response.integration.config.siteEvent)); setSaved(true); onSaved(response.integration);
    } catch { setError(t("site_events.invalid")); }
    finally { setBusy(false); }
  }
  return { draft, change, save, busy, submitted, saved, error, valid, catalog, catalogStatus, loadCatalog };
}

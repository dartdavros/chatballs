import { useState } from "react";
import { api, ApiError } from "../../../api/client";
import { t } from "../../../i18n";
import type { Integration } from "../model";

export function useSpeechConnection(initial: Integration | null, onSaved: () => void) {
  const [connection, setConnection] = useState(initial);
  const [name, setName] = useState(initial?.name ?? "");
  const [folder, setFolder] = useState(initial?.config.folderId ?? "");
  const [secret, setSecret] = useState("");
  const [busy, setBusy] = useState(false);
  const [checking, setChecking] = useState<"stt" | "tts" | null>(null);
  const [error, setError] = useState("");
  const [fields, setFields] = useState<Record<string, string>>({});
  const dirty = !connection || name !== connection.name || folder !== connection.config.folderId || Boolean(secret);

  async function save() {
    if (busy) return;
    const errors: Record<string, string> = {};
    if (!name.trim()) errors.name = t("speech.required");
    if (!folder.trim()) errors.folder = t("speech.required");
    if (!connection?.hasSecret && !secret.trim()) errors.secret = t("speech.required");
    setFields(errors);
    if (Object.keys(errors).length) return;
    setBusy(true); setError("");
    try {
      const response = await api<{ integration: Integration }>(connection ? `/api/v1/integrations/${connection.id}/` : "/api/v1/integrations/", {
        method: connection ? "PATCH" : "POST",
        body: JSON.stringify({ name, provider: "YANDEX_SPEECHKIT", config: { ...connection?.config, folderId: folder }, ...(secret.trim() ? { secret } : {}) }),
      });
      setConnection(response.integration); setName(response.integration.name);
      setFolder(response.integration.config.folderId ?? ""); setSecret(""); onSaved();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t("common.could_not_save"));
    } finally { setBusy(false); }
  }

  async function check(capability: "stt" | "tts" = "stt") {
    if (!connection || dirty || checking) return;
    setChecking(capability); setError("");
    try {
      const result = await api<{ integration: Integration }>(`/api/v1/integrations/${connection.id}/test/`, { method: "POST", body: JSON.stringify({ capability }) });
      setConnection(result.integration); onSaved();
    } catch (caught) { setError(caught instanceof Error ? caught.message : t("common.request_failed")); }
    finally { setChecking(null); }
  }
  return { connection, name, setName, folder, setFolder, secret, setSecret, busy, checking: Boolean(checking), checkingCapability: checking, error, fields, dirty, save, check };
}

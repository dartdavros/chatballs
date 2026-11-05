import { useState } from "react";

import { api } from "../../api/client";
import { t } from "../../i18n";
import { ConnectionRouteFields } from "./ConnectionRouteFields";
import { FormField } from "../../shared/form-controls";
import { Button, CopyButton } from "../../shared/ui-controls";
import { validRecording, WebRecordingFields, type WebRecordingDraft } from "./speech/WebRecordingFields";
import {
  connectionGroupSettings, formatAllowedOrigins, invalidAllowedOrigin, parseAllowedOrigins,
  webWidgetSnippet, type Integration,
} from "./model";

export function WebIntegrationBasics({ integration, onSaved }: {
  integration: Integration;
  onSaved: (updated: Integration) => void;
}) {
  const [name, setName] = useState(integration.name);
  const [allowedOrigins, setAllowedOrigins] = useState(formatAllowedOrigins(integration.config.allowedOrigins));
  const [channelId, setChannelId] = useState(integration.channel ? String(integration.channel.id) : "");
  const [groupId, setGroupId] = useState(integration.channel?.groupId ? String(integration.channel.groupId) : "");
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState<WebRecordingDraft>({
    microphoneMode: integration.config.microphoneMode ?? "off",
    maxSize: String((integration.config.maxRecordingBytes ?? 10485760) / 1048576),
    maxSeconds: String(integration.config.maxDictationSeconds ?? 60),
    answerPlaybackEnabled: integration.config.answerPlaybackEnabled ?? false,
  });
  const [error, setError] = useState<string | null>(null);
  const origins = parseAllowedOrigins(allowedOrigins);
  const badOrigin = invalidAllowedOrigin(origins);
  const ready = Boolean(name.trim() && origins.length && !badOrigin && validRecording(recording));
  const hasAgent = Boolean(channelId && (String(integration.channel?.id) !== channelId || integration.channel?.hasAgent));
  const snippet = integration.webChatWidget ? webWidgetSnippet(integration.webChatWidget.publicKey) : "";

  async function save() {
    if (!ready) return;
    setBusy(true);
    setError(null);
    try {
      const response = await api<{ integration: Integration }>(`/api/v1/integrations/${integration.id}/`, {
        method: "PATCH",
        body: JSON.stringify({ name: name.trim(), channelId: channelId ? Number(channelId) : null,
          ...connectionGroupSettings(integration, channelId, groupId), config: { ...integration.config, allowedOrigins: origins,
            microphoneMode: recording.microphoneMode, maxRecordingBytes: Number(recording.maxSize) * 1048576, maxDictationSeconds: Number(recording.maxSeconds), answerPlaybackEnabled: recording.answerPlaybackEnabled } }),
      });
      onSaved(response.integration);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : t("common.could_not_save"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="portal-settings-card web-integration-basics">
      <FormField label={t("common.title")} value={name} onChange={setName} />
      <div>
        <FormField
          label={t("settings.allowed_domains")}
          value={allowedOrigins}
          onChange={setAllowedOrigins}
          error={badOrigin && t("settings.unclear_domain", { domain: badOrigin })}
          placeholder={t("settings.example_com_example_com_comma")}
        />
        <div className="integration-form-hint">{t("settings.sites_where_widget_may_open")}</div>
      </div>
      <ConnectionRouteFields initial={integration} channelId={channelId} onChannel={setChannelId} groupId={groupId} onGroup={setGroupId} />
      <WebRecordingFields value={recording} onChange={setRecording} hasAgent={hasAgent} />
      {snippet && <div className="web-integration-snippet">
        <FormField label={t("settings.embed_snippet_site")} mono value={snippet} />
        <CopyButton value={snippet} label={t("common.copy")} className="secondary-button" />
      </div>}
      {error && <div className="integration-form-error">{error}</div>}
      <div className="portal-settings-actions">
        <Button variant="primary" disabled={!ready || busy} onClick={() => void save()}>
          {busy ? t("ai.saving") : t("common.save")}
        </Button>
      </div>
    </div>
  );
}

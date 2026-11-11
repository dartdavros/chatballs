import { useState } from "react";
import { isManager } from "../../auth/access";
import { t } from "../../i18n";
import { EmptyState } from "../../shared/ui";
import { Button, UnderlineTabs } from "../../shared/ui-controls";
import type { SessionUser } from "../../types";
import { useIntegrations } from "../settings/useIntegrations";
import { AddIntegrationButton } from "./AddIntegrationButton";
import { IntegrationForm } from "./IntegrationForm";
import { IntegrationList } from "./IntegrationList";
import { IntegrationWorkspaceLayout } from "./IntegrationWorkspaceLayout";
import type { ServerKind } from "./external/types";
import type { Integration, IntegrationKind } from "./model";
import { SpeechSettingsContent } from "./speech/SpeechSettingsContent";
import { WORKSPACE_PROVIDERS, workspaceItems, workspaceLabels, type IntegrationWorkspaceMode, type ServerFilter } from "./workspaceModel";
import "./styles.css";
import "./integrations-tabs.css";

type Props = {
  mode: IntegrationWorkspaceMode;
  user: SessionUser;
  openWebIntegration: (id: number) => void;
  openServer: (id: number) => void;
  createServer: (kind: ServerKind) => void;
};

export function IntegrationWorkspacePage(props: Props) {
  if (!isManager(props.user)) return <EmptyState title={t("settings.settings_available_owner_administrators")} />;
  return <WorkspaceContent key={`${props.user.organizationPublicId}:${props.mode}`} {...props} />;
}

function WorkspaceContent({ mode, openWebIntegration, openServer, createServer }: Props) {
  const integrations = useIntegrations(true);
  const [form, setForm] = useState<{ kind: IntegrationKind; initial: Integration | null } | null>(null);
  const [serverFilter, setServerFilter] = useState<ServerFilter>("all");
  const labels = workspaceLabels(mode);
  const items = workspaceItems(integrations.items, mode, serverFilter);
  const newForm = () => setForm({ kind: mode === "providers" ? "LLM_PROVIDER" : "MESSENGER", initial: null });
  const onEdit = (item: Integration) => {
    if (item.provider === "WEB") openWebIntegration(item.id);
    else if (item.kind === "EXTERNAL_SERVER") openServer(item.id);
    else setForm({ kind: item.kind, initial: item });
  };

  return <IntegrationWorkspaceLayout>
    {form?.kind === "SPEECH_PROVIDER"
      ? <SpeechSettingsContent key={form.initial?.id ?? "new"} initial={form.initial}
        onBack={() => setForm(null)} onSaved={integrations.reload} />
      : <>
        <header className="settings-head">
          <div><h2>{labels.title}</h2><p>{labels.lead}</p></div>
          {mode === "servers" ? <AddIntegrationButton onServer={createServer} label={labels.add} />
            : <Button variant="primary" icon="plus" onClick={newForm}>{labels.add}</Button>}
        </header>
        {mode === "servers" && <UnderlineTabs className="integrations-tabs" value={serverFilter} onChange={setServerFilter}
          items={[{ key: "all", label: t("common.all") }, { key: "MCP", label: t("navigation.mcp_servers") },
            { key: "HTTP", label: t("navigation.http_requests") }]} />}
        <IntegrationList items={items} providers={mode === "providers"} servers={mode === "servers"}
          loading={integrations.loading} failed={integrations.failed}
          empty={labels.empty} reload={integrations.reload} onEdit={onEdit} />
      </>}
    {form && form.kind !== "SPEECH_PROVIDER" && <IntegrationForm key={form.initial?.id ?? "new"}
      initial={form.initial} kind={form.kind} allowedProviders={WORKSPACE_PROVIDERS[mode]}
      title={form.initial ? labels.edit : labels.add}
      onSpeechKit={() => setForm({ kind: "SPEECH_PROVIDER", initial: null })}
      onClose={() => setForm(null)} onSaved={() => { setForm(null); integrations.reload(); }} />}
  </IntegrationWorkspaceLayout>;
}

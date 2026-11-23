import { t } from "../../i18n";
import { ListEmptyState } from "../../shared/ListEmptyState";
import { Button } from "../../shared/ui-controls";
import { AddIntegrationButton } from "./AddIntegrationButton";
import type { ServerKind } from "./external/types";
import type { ServerFilter } from "./workspaceModel";

const serverEmptyStates = {
  MCP: { icon: "server", kind: "mcp", title: "navigation.mcp_empty", text: "servers.mcp_hint", add: "navigation.add_mcp" },
  HTTP: { icon: "swap", kind: "http", title: "navigation.http_empty", text: "servers.http_hint", add: "navigation.add_http" },
} as const;

export function ServerListEmptyState({ filter, title, createServer }: {
  filter: ServerFilter;
  title: string;
  createServer: (kind: ServerKind) => void;
}) {
  if (filter === "all") {
    return <ListEmptyState icon="server" title={title} text={t("navigation.tools_empty_hint")}
      action={<AddIntegrationButton label={t("navigation.add_tool")} onServer={createServer} />} />;
  }

  const state = serverEmptyStates[filter];
  return <ListEmptyState icon={state.icon} title={t(state.title)} text={t(state.text)}
    action={<Button variant="primary" onClick={() => createServer(state.kind)}>{t(state.add)}</Button>} />;
}

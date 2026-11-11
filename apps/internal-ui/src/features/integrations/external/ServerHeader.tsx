import { t, tn } from "../../../i18n";
import { Icon } from "../../../shared/icons";
import { CopyButton, ToneBadge } from "../../../shared/ui-controls";
import { STATUS_META } from "../model";
import type { ServerEditor } from "./useServerEditor";

export function ServerHeader({ editor, onBack }: { editor: ServerEditor; onBack: () => void }) {
  const server = editor.integration?.externalServer ?? editor.draft.externalServer;
  const mcp = server.type === "mcp";
  const name = editor.integration?.name || t(mcp ? "servers.new_mcp" : "servers.new_http");
  const invalid = !mcp && editor.dirty && Object.values(editor.errors).some((messages) => messages.length > 0);
  const status = invalid ? { bg: "var(--error-bg)", color: "var(--error-text)", label: t("servers.unsaved") } : editor.integration
    ? editor.integration.isActive ? STATUS_META[editor.integration.status]
      : { bg: "var(--n-9)", color: "var(--n-4)", label: t("settings.disabled") }
    : { bg: "var(--n-9)", color: "var(--n-4)", label: t("common.draft") };
  return <header className="web-integration-head">
    <nav className="portal-breadcrumbs">
      <button className="link is-strong" type="button" onClick={onBack}>{t("navigation.tools")}</button><span>/</span><b>{name}</b>
    </nav>
    <div className="web-integration-title">
      <span className="server-title-icon"><Icon name={mcp ? "server" : "swap"} size={17} /></span><h2>{name}</h2>
      <ToneBadge className="web-integration-status" bg={status.bg} color={status.color}>{status.label}</ToneBadge><span className="web-integration-agent">{t(mcp ? "servers.new_mcp" : "servers.new_http")} · {tn("servers.count", mcp ? server.tools?.length ?? 0 : 1)}</span>
    </div>
    {server.url && <div className="web-integration-embed"><span className="web-integration-embed-code"><code>{mcp ? "" : `${server.method ?? "GET"} `}{server.url}</code><CopyButton value={server.url} className="web-integration-copy" /></span><span>{t(mcp ? "servers.address_note" : "servers.request_note")}</span></div>}
  </header>;
}

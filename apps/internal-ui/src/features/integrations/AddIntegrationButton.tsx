import { Dropdown } from "antd";
import { useState } from "react";
import { t } from "../../i18n";
import { Icon } from "../../shared/icons";
import { Button } from "../../shared/ui-controls";
import type { ServerKind } from "./external/types";
import "./add-integration.css";

export function AddIntegrationButton({ onEntry, onServer, label }: {
  onEntry?: () => void; onServer: (kind: ServerKind) => void; label?: string;
}) {
  const [open, setOpen] = useState(false);
  const option = (icon: "message" | "server" | "swap", title: string, hint: string) =>
    <button type="button"><i><Icon name={icon} size={15} /></i><span><strong>{title}</strong><small>{hint}</small></span></button>;
  return <Dropdown open={open} onOpenChange={setOpen} trigger={["click"]} overlayClassName="app-dropdown is-server-add" menu={{
    onClick: ({ key }) => { setOpen(false); if (key === "entry") onEntry?.(); else onServer(key as ServerKind); },
    items: [
    ...(onEntry ? [{ type: "group" as const, label: t("servers.entry"), children: [
      { key: "entry", label: option("message", t("servers.entry_title"), t("servers.entry_hint")) },
    ] }, { type: "divider" as const }] : []),
    { type: "group", label: t("navigation.tools"), children: [
      { key: "mcp", label: option("server", t("servers.new_mcp"), t("servers.mcp_hint")) },
      { key: "http", label: option("swap", t("servers.new_http"), t("servers.http_hint")) },
    ] },
  ] }}><Button className="row-menu-button integration-add-button" variant="primary" icon="plus" aria-expanded={open}>{label ?? t("servers.add")}<Icon name="chevron" size={14} /></Button></Dropdown>;
}

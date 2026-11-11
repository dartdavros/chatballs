import { useState } from "react";
import { fmt, t } from "../../../i18n";
import type { SectionMenuItem } from "../../../shared/SectionMenu";
import { IntegrationPageLayout } from "../IntegrationPageLayout";
import type { Integration } from "../model";
import { DeleteIntegrationDialog } from "../DeleteIntegrationDialog";
import { HttpParameters } from "./HttpParameters";
import { HttpToolForm } from "./HttpToolForm";
import { McpTools } from "./McpTools";
import { ServerConnection } from "./ServerConnection";
import { ServerHeader } from "./ServerHeader";
import { useServerEditor } from "./useServerEditor";
import type { ServerKind } from "./types";
import "./styles.css";
import "./tools.css";
import "./parameters.css";

type Section = "main" | "tools" | "parameters" | "delete";

export function ExternalServerPage({ initial, kind, integrations, onCreated, onBack }: {
  initial: Integration | null; kind: ServerKind; integrations: Integration[];
  onCreated: (id: number) => void; onBack: () => void;
}) {
  const editor = useServerEditor(kind, initial, onCreated);
  const [section, setSection] = useState<Section>("main");
  const [deleting, setDeleting] = useState(false);
  const mcp = kind === "mcp";
  const items: SectionMenuItem<Section>[] = [
    { key: "main", label: t(mcp ? "servers.connection" : "servers.tool"), icon: "settings" },
    mcp ? { key: "tools", label: t("ai.tools"), icon: "wrench", hint: { text: fmt.number(editor.integration?.externalServer?.tools?.length ?? 0) }, divider: true }
      : { key: "parameters", label: t("servers.parameters"), icon: "list", hint: { text: fmt.number(editor.draft.externalServer.parameters?.length ?? 0) }, divider: true },
    { key: "delete", label: t(mcp ? "servers.delete" : "servers.delete_tool"), icon: "trash", danger: true, disabled: !editor.integration },
  ];
  return <>
    <IntegrationPageLayout className="external-server-page"
      header={<ServerHeader editor={editor} onBack={onBack} />}
      items={items} activeKey={section} note={t("servers.changes_note")}
      onSelect={(key) => key === "delete" ? setDeleting(true) : setSection(key)}>
        {section === "main" && (mcp ? <ServerConnection editor={editor} /> : <HttpToolForm editor={editor} />)}
        {section === "tools" && <McpTools editor={editor} openConnection={() => setSection("main")} />}
        {section === "parameters" && <HttpParameters editor={editor} integrations={integrations} />}
    </IntegrationPageLayout>
    {deleting && editor.integration && <DeleteIntegrationDialog integration={editor.integration} onClose={() => setDeleting(false)} onDeleted={onBack} />}
  </>;
}

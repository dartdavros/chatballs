import { hasRequestBody } from "./httpMethods";
import { t } from "../../../i18n";
import type { Integration } from "../model";
import { sourceKey, sourceLabel } from "./model";
import type { ExternalServer, ToolParameter } from "./types";

export function parameterExample(parameter: ToolParameter): string | number | boolean {
  if (parameter.type === "boolean") return false;
  if (parameter.type === "number") return 10482;
  if (parameter.source.type === "contact") {
    if (parameter.source.field === "email") return "irina.sokolova@mail.ru";
    if (parameter.source.field === "phone") return "+79991234567";
    return t("site_fields.example_name");
  }
  return "10482";
}

export function RequestPreview({ server, integrations, compact = false }: { server: ExternalServer; integrations: Integration[]; compact?: boolean }) {
  const parameters = server.parameters ?? [];
  const part = (parameter: ToolParameter, value: string) => <mark key={parameter.name} className={parameter.source.type === "ai" ? "is-ai" : "is-system"}>{value}</mark>;
  const pathParts = server.url.split(/(\{[^{}]*\})/g).map((segment, i) => {
    const parameter = parameters.find((p) => `{${p.name}}` === segment);
    return <span key={`path-${i}`}>{parameter ? part(parameter, encodeURIComponent(String(parameterExample(parameter)))) : segment}</span>;
  });
  const query = parameters.filter((p) => p.location === "query" && !server.url.includes(`{${p.name}}`));
  const body = parameters.filter((p) => p.location === "body");
  const legend = [...new Map(parameters.map((p) => [sourceKey(p.source), p])).values()];
  const web = parameters.find((p) => p.source.type === "web_field")?.source;
  const connection = web?.type === "web_field" ? integrations.find((i) => i.id === web.integrationId) : undefined;
  return <div className={`server-request-preview${compact ? " is-compact" : ""}`}>
    <strong>{t(compact ? "servers.parameter_preview" : "servers.preview")}</strong>
    {!compact && <small>{connection ? t("servers.preview_client_hint", { connection: connection.name }) : t("servers.preview_hint")}</small>}
    <div className="server-preview-code"><code>{server.method ?? "GET"}{" "}{pathParts}
      {query.map((p, i) => <span key={p.name}>{i === 0 && !server.url.includes("?") ? "?" : "&"}{encodeURIComponent(p.name)}={part(p, encodeURIComponent(String(parameterExample(p))))}</span>)}
    </code>
      {hasRequestBody(server.method) && body.length > 0 && <pre>{"{"}{body.map((p, i) => <span key={p.name}>{i > 0 ? ", " : ""}{JSON.stringify(p.name)}: {part(p, JSON.stringify(parameterExample(p)))}</span>)}{"}"}</pre>}
    </div>
    <div className="server-preview-legend">{legend.map((p) => <span key={sourceKey(p.source)} className={p.source.type === "ai" ? "is-ai" : "is-system"}>{!compact && <i />}{p.source.type === "ai" ? t("servers.preview_ai") : compact
      ? t("servers.parameter_example", { field: sourceLabel(p.source, integrations) })
      : t("servers.preview_system", { name: sourceLabel(p.source, integrations) })}</span>)}</div>
  </div>;
}

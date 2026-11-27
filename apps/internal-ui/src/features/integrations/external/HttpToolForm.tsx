import { useId } from "react";
import { t } from "../../../i18n";
import { FormField, SelectField, TextAreaField } from "../../../shared/form-controls";
import { HTTP_METHODS, type HttpMethod } from "./httpMethods";
import { ServerHeaders } from "./ServerHeaders";
import { ServerEnabled, ServerErrors, ServerSaveActions } from "./ServerFormParts";
import { ServerWarning } from "./ServerWarning";
import type { ServerEditor } from "./useServerEditor";
import { TemplateAddressField } from "./TemplateAddressField";

export function HttpToolForm({ editor }: { editor: ServerEditor }) {
  const requestLabelId = useId();
  const { draft, change, busy, errors } = editor;
  const server = draft.externalServer;
  const update = (next: Partial<typeof server>) => change({ ...draft, externalServer: { ...server, ...next } });
  return <div className="portal-settings-inner server-content server-http-content">
    <div className="portal-settings-heading"><h3>{t("servers.tool")}</h3><p>{t("servers.http_lead")}</p></div>
    <div className="portal-settings-card server-form">
      <div className="server-two-fields">
        <div><FormField label={t("servers.display_name")} value={draft.name} error={errors.name?.join(" ")} disabled={busy} onBlur={() => editor.blur("name")} onChange={(name) => change({ ...draft, name })} /><small>{t("servers.display_name_hint")}</small></div>
        <div><FormField label={t("servers.tool_name")} value={server.toolName ?? ""} error={errors.toolName?.join(" ")} mono disabled={busy} onBlur={() => editor.blur("toolName")} onChange={(toolName) => update({ toolName })} />{!errors.toolName?.length && <small>{t("servers.tool_name_hint")}</small>}</div>
      </div>
      <div onBlur={() => editor.blur("description")}><TextAreaField label={t("servers.ai_description")} value={server.description} disabled={busy} onChange={(description) => update({ description })} />
        <small>{t("servers.ai_description_hint")}</small><ServerErrors messages={errors.description} /></div>
      <ServerEnabled editor={editor} />
    </div>
    <div className="portal-settings-card server-form">
      <strong>{t("servers.request")}</strong>
      <div>
        <span className="server-method-label" id={requestLabelId}>{t("servers.method_address")}</span>
        <div className="server-request-fields" role="group" aria-labelledby={requestLabelId}>
          <SelectField label={t("servers.http_method")} value={server.method ?? "GET"} disabled={busy}
            options={HTTP_METHODS.map(method => [method, method])}
            onChange={(method) => update({ method: method as HttpMethod, readOnly: method === "POST" && server.readOnly })} />
          <TemplateAddressField label={t("servers.request_url")} value={server.url} disabled={busy} invalid={Boolean(errors.url?.length)} onBlur={() => editor.blur("url")} onChange={(url) => update({ url })} />
        </div>
        {!errors.url?.length && <small>{t("servers.url_hint")}</small>}
        <ServerErrors messages={errors.url} />
        {server.method === "POST" && <label className="server-post-check"><input type="checkbox" checked={Boolean(server.readOnly)} disabled={busy}
          onChange={(event) => update({ readOnly: event.target.checked })} /><span><strong>{t("servers.post_read")}</strong><small>{t("servers.post_read_hint")}</small></span></label>}
      </div>
      <ServerHeaders headers={server.headers} onChange={(headers) => update({ headers })} disabled={busy} mcp={false} />
      <ServerErrors messages={errors.headers} />
      <ServerSaveActions editor={editor} />
    </div>
    <ServerWarning />
  </div>;
}

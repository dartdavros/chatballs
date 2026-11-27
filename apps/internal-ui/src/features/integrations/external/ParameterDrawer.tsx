import { hasRequestBody } from "./httpMethods";
import { Drawer } from "antd";
import { useState } from "react";
import { t } from "../../../i18n";
import { FormField, SelectField, SwitchButton, TextAreaField } from "../../../shared/form-controls";
import { Button, IconButton } from "../../../shared/ui-controls";
import { Segmented } from "../../../shared/ui";
import { Icon } from "../../../shared/icons";
import type { Integration } from "../model";
import { ParameterSourceSelect } from "./ParameterSourceSelect";
import { RequestPreview } from "./RequestPreview";
import { parameterError, placeholders } from "./validation";
import type { ExternalServer, ToolParameter } from "./types";

export function ParameterDrawer({ initial, index, name, server, integrations, onClose, onSave, onDelete }: {
  initial: ToolParameter; index: number; name: string; server: ExternalServer; integrations: Integration[];
  onClose: () => void; onSave: (parameter: ToolParameter) => void; onDelete: () => void;
}) {
  const [parameter, setParameter] = useState(initial);
  const inPath = placeholders(server.url).includes(parameter.name);
  const bound = parameter.source.type !== "ai";
  const next = { ...parameter, name: parameter.name.trim(), ...(inPath ? { required: true, location: "path" as const } : {}) };
  const error = parameterError(next, server.parameters ?? [], index, server.url, server.method ?? "GET");
  const customerSource = parameter.source.type === "ai" ? { type: "contact" as const, field: "name" as const } : parameter.source;
  return <Drawer open width={520} closable={false} extra={<IconButton icon="close" label={t("common.close")} onClick={onClose} />}
    title={<div><small>{t("servers.parameter_title", { name })}</small><strong>{parameter.name || t("servers.add_parameter")}</strong></div>}
    onClose={onClose} className="server-parameter-drawer" footer={<div className="server-actions">
      <Button variant="danger-outline" onClick={onDelete}>{t("common.delete")}</Button><span className="server-spacer" />
      <Button variant="secondary" onClick={onClose}>{t("common.cancel")}</Button>
      <Button variant="primary" disabled={Boolean(error)} onClick={() => onSave(next)}>{t("common.save")}</Button>
    </div>}>
    <div className="server-form">
      <div className="server-two-fields">
        <div><FormField label={t("servers.parameter_name")} mono value={parameter.name} onChange={(name) => setParameter({ ...parameter, name })} />
          {inPath && <small>{t("servers.parameter_address", { placeholder: `{${parameter.name}}` })}</small>}</div>
        <SelectField label={t("servers.parameter_type")} value={parameter.type} options={[["string", t("servers.type_string")], ["number", t("servers.type_number")], ["boolean", t("servers.type_boolean")]]}
          onChange={(type) => setParameter({ ...parameter, type: type as ToolParameter["type"] })} />
      </div>
      <div><strong>{t("servers.parameter_source")}</strong>
        <label className={`server-source-radio${!bound ? " is-selected" : ""}`}><input type="radio" name="source" checked={!bound} onChange={() => setParameter({ ...parameter, source: { type: "ai" } })} /><span><strong>{t("servers.ai_source")}</strong><small>{t("servers.ai_source_hint")}</small></span></label>
        <div className={`server-source-radio${bound ? " is-selected" : ""}`}>
          <input type="radio" name="source" aria-label={t("servers.customer_source")} checked={bound} onChange={() => setParameter({ ...parameter, source: customerSource })} />
          <div><strong>{t("servers.customer_source")}</strong><small>{t("servers.bound_hint")}</small>
            {bound && <ParameterSourceSelect details source={parameter.source} integrations={integrations} onChange={(source) => setParameter({ ...parameter, source })} />}
            {parameter.source.type === "web_field" && <small className="server-drawer-web-warning"><Icon name="alert" size={12} /><span>{t("servers.parameter_web_hint")}</span></small>}
          </div>
        </div>
      </div>
      <div><TextAreaField label={t("servers.ai_description")} value={bound ? t("servers.bound_description") : parameter.description} disabled={bound} onChange={(description) => setParameter({ ...parameter, description })} /><small>{t("servers.parameter_description_hint")}</small></div>
      <div className="server-parameter-location"><strong>{t("servers.parameter_location")}</strong><Segmented className="is-content-width" value={inPath ? "path" : parameter.location}
        items={[["path", t("servers.path")], ["query", t("servers.query")], ["body", t("servers.body")]]}
        disabledKeys={inPath ? ["path", "query", "body"] : hasRequestBody(server.method) ? [] : ["body"]}
        setValue={(location) => setParameter({ ...parameter, location })} /><small>{t("servers.path_hint")}</small></div>
      <div className="server-enabled"><span><strong>{t("servers.parameter_required")}</strong><small>{t("servers.required_hint")}</small></span>
        <SwitchButton className="ui-switch" label={t("servers.parameter_required")} checked={inPath || parameter.required} disabled={inPath} onClick={() => setParameter({ ...parameter, required: !parameter.required })} /></div>
      {error && <div className="server-errors" role="alert">{error}</div>}
      <RequestPreview compact server={{ ...server, parameters: [next] }} integrations={integrations} />
    </div>
  </Drawer>;
}

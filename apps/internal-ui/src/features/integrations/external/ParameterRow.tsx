import { hasRequestBody } from "./httpMethods";
import { Dropdown } from "antd";
import { useState } from "react";
import { t } from "../../../i18n";
import { SelectField, SwitchButton, TextAreaField } from "../../../shared/form-controls";
import { Icon } from "../../../shared/icons";
import { sourceLabel } from "./model";
import type { Integration } from "../model";
import { ParameterSourceSelect } from "./ParameterSourceSelect";
import type { ToolParameter } from "./types";

export function ParameterRow({ parameter, integrations, disabled, method, inPath, first, last, selected, onChange, onAction }: {
  parameter: ToolParameter; integrations: Integration[]; disabled: boolean; method: string; inPath: boolean; first: boolean; last: boolean;
  selected: boolean;
  onChange: (parameter: ToolParameter) => void; onAction: (key: string) => void;
}) {
  const bound = parameter.source.type !== "ai";
  const [menuOpen, setMenuOpen] = useState(false);
  return <div className={`server-parameter-row${selected ? " is-selected" : menuOpen ? " is-menu-open" : ""}`}>
    <button className="link is-mono is-neutral" type="button" disabled={disabled} onClick={() => onAction("open")}>{parameter.name}</button>
    <SelectField label={`${parameter.name}: ${t("servers.parameter_type")}`} value={parameter.type} disabled={disabled}
      options={[["string", t("servers.type_string")], ["number", t("servers.type_number")], ["boolean", t("servers.type_boolean")]]}
      onChange={(type) => onChange({ ...parameter, type: type as ToolParameter["type"] })} />
    <SwitchButton className="ui-switch is-compact" label={`${parameter.name}: ${t("servers.parameter_required")}`}
      checked={parameter.required || inPath} disabled={disabled || inPath} onClick={() => onChange({ ...parameter, required: !parameter.required })} />
    <SelectField label={`${parameter.name}: ${t("servers.parameter_location")}`} value={inPath ? "path" : parameter.location} disabled={disabled || inPath}
      options={[["path", t("servers.path")], ["query", t("servers.query")], ...(hasRequestBody(method) ? [["body", t("servers.body")] as [string, string]] : [])]}
      onChange={(location) => onChange({ ...parameter, location: location as ToolParameter["location"] })} />
    <ParameterSourceSelect label={`${parameter.name}: ${t("servers.parameter_source")}`} source={parameter.source} integrations={integrations} disabled={disabled}
      onChange={(source) => onChange({ ...parameter, source })} />
    <Dropdown trigger={["click"]} onOpenChange={setMenuOpen} overlayClassName="app-dropdown server-parameter-menu" menu={{ onClick: ({ key }) => { setMenuOpen(false); onAction(key); }, items: [
      { key: "open", icon: <Icon name="edit" size={15} />, label: t("servers.open_parameter"), disabled },
      { key: "duplicate", icon: <Icon name="copy" size={15} />, label: t("servers.duplicate"), disabled },
      { key: "up", icon: <span className="server-arrow-up"><Icon name="arrowDown" size={15} /></span>, label: t("servers.move_up"), disabled: disabled || first },
      { key: "down", icon: <Icon name="arrowDown" size={15} />, label: <span>{t("servers.move_down")}{last && <small className="server-menu-hint">{t("servers.already_last")}</small>}</span>, disabled: disabled || last },
      { type: "divider" }, { key: "delete", icon: <Icon name="trash" size={15} />, label: t("common.delete"), danger: true, disabled },
    ] }}><button className="row-menu-button" type="button" disabled={disabled} aria-label={`${parameter.name}: ${t("settings.integration_actions")}`}><Icon name="more" /></button></Dropdown>
    <div className="server-parameter-description"><TextAreaField label={t("servers.ai_description")} value={bound ? t("servers.bound_row_description", { field: sourceLabel(parameter.source, integrations) }) : parameter.description}
      disabled={disabled || bound} onChange={(description) => onChange({ ...parameter, description })} /></div>
  </div>;
}

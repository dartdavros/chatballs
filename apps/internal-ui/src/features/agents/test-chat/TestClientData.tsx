import { useId, useState } from "react";
import type { ClientField } from "@chatballs/shared";
import { t } from "../../../i18n";
import { Icon } from "../../../shared/icons";
import { contactFields, dataSummary, valueKey, type TestConnection, type TestValues } from "./model";
import { TestClientField } from "./TestClientField";

export function TestClientData({ connections, values, onChange, disabled, preview = true }: {
  connections: TestConnection[]; values: TestValues; disabled: boolean; preview?: boolean;
  onChange: (values: TestValues) => void;
}) {
  const [expanded, setExpanded] = useState(true);
  const id = useId();
  function fieldControl(field: ClientField, key: string) {
    return <TestClientField key={key} field={field} id={`${id}-${key}`} value={values[key] ?? ""}
      disabled={disabled} onChange={(value) => onChange({ ...values, [key]: value })} />;
  }
  return <section className="agent-test-data">
    <button type="button" className="agent-test-data-heading" aria-expanded={expanded} aria-controls={`${id}-fields`}
      onClick={() => setExpanded(!expanded)}>
      <Icon name="user" size={15} strokeWidth={1.9} />
      <span><strong>{t("agent_test.client_data")}</strong>{preview && <small>{expanded ? t("agent_test.data_summary") : dataSummary(values, connections)}</small>}</span>
      <span className={expanded ? "is-expanded" : ""}><Icon name="chevron" size={14} strokeWidth={2.2} /></span>
    </button>
    {expanded && <div id={`${id}-fields`} className="agent-test-fields">
      {preview && <small className="agent-test-data-hint">{t("agent_test.data_hint")}</small>}
      {contactFields().map((field) => fieldControl(field, field.key))}
      {connections.filter((connection) => connection.fields.length).map((connection) => <div className="agent-test-custom" key={connection.id}>
        <strong className="agent-test-group">{t("settings.site_data")}{connections.filter((item) => item.fields.length).length > 1 && ` · ${connection.name}`}</strong>
        {connection.fields.map((field) => fieldControl(field, valueKey(connection.id, field.key)))}
      </div>)}
      <div className="agent-test-data-footer">
        <small>{connections.filter((connection) => connection.fields.length).map((connection) =>
          <span key={connection.id}>{t("agent_test.custom_source", { name: connection.name })}</span>)}</small>
        <button type="button" className="link" disabled={disabled} onClick={() => onChange({})}>{t("agent_test.reset_data")}</button>
      </div>
    </div>}
  </section>;
}

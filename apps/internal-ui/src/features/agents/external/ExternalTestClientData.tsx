import { useId, useState } from "react";
import { t } from "../../../i18n";
import { Icon } from "../../../shared/icons";
import { HelpTrigger } from "../../settings/external-agent/HelpTrigger";
import { et } from "../../settings/external-agent/copy";
import { TestClientField } from "../test-chat/TestClientField";
import type { TestValues } from "../test-chat/model";
import { fieldKey, testFields, type TestDefinition } from "./test-model";

export function ExternalTestClientData({ definition, values, change, disabled }: {
  definition: TestDefinition; values: TestValues; change: (values: TestValues) => void; disabled: boolean;
}) {
  const id = useId(), [expanded, setExpanded] = useState(true);
  const fields = testFields(definition);
  const sources = [...new Map(definition.customFields.map(field => [field.sourceConnectionId, field.sourceName])).entries()];
  const render = (key: string) => {
    const field = fields.find(item => item.key === key)!;
    return <TestClientField key={key} field={field} id={`${id}-${key}`} value={values[key] ?? ""} disabled={disabled}
      onChange={value => change({ ...values, [key]: value })} />;
  };
  return <section className="agent-test-data">
    <button type="button" className="agent-test-data-heading" aria-expanded={expanded} aria-controls={`${id}-fields`} onClick={() => setExpanded(!expanded)}>
      <Icon name="user" size={15} strokeWidth={1.9} /><span><strong>{t("agent_test.client_data")}</strong></span>
      <span className={expanded ? "is-expanded" : ""}><Icon name="chevron" size={14} strokeWidth={2.2} /></span>
    </button>
    {expanded && <div id={`${id}-fields`} className="agent-test-fields">
      <small className="agent-test-data-hint">{et(fields.length ? "agent.fieldsHelp" : "test.testDataEmpty")}</small>
      {definition.standardFields.map(render)}
      {sources.map(([source, name]) => <div key={source}>
        <span className="external-help-title"><strong className="agent-test-group">{t("settings.site_data")} · {name}</strong><HelpTrigger topic="webFields" /></span>
        {definition.customFields.filter(field => field.sourceConnectionId === source).map(field => render(fieldKey(source, field.fieldId)))}
      </div>)}
    </div>}
  </section>;
}

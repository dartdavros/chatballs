import { FormField, SelectField } from "../../../shared/form-controls";
import { et } from "./copy";
import type { ExternalBinding } from "./model";

export function PolicyTarget({ name, bindings, agentId, disabled, select }: {
  name: string; bindings: ExternalBinding[]; agentId: number; disabled: boolean; select: (id: number) => void;
}) {
  return <div data-policy-agent={agentId}><div className="administration-fields">
    <FormField label={et("policy.policyConnection")} value={name} />
    <SelectField label={et("policy.policyAgent")} value={String(agentId)} disabled={disabled}
      options={bindings.map(binding => [String(binding.agentId), binding.agentName])} onChange={value => select(Number(value))} />
  </div><p className="settings-section-note">{et("policy.policyScope")}</p></div>;
}

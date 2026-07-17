import { SelectField } from "../../../shared/form-controls";
import type { Integration } from "../../integrations/model";
import { CREDENTIAL_MODE_OPTIONS, type CredentialMode } from "../model";
import { CreateAgentStepCard } from "./CreateAgentStepCard";

export function ModelStep({
  credentialMode,
  setCredentialMode,
  providerIntegrationId,
  setProviderIntegrationId,
  integrations,
}: {
  credentialMode: CredentialMode;
  setCredentialMode: (mode: CredentialMode) => void;
  providerIntegrationId: number | null;
  setProviderIntegrationId: (id: number | null) => void;
  integrations: Integration[];
}) {
  const integrationOptions: Array<[string, string]> = [
    ["", "Выберите интеграцию"],
    ...integrations.map((item) => [String(item.id), item.name] as [string, string]),
  ];
  return (
    <CreateAgentStepCard number={2} title="AI-провайдер" text="CustoAI готов к работе сразу. При необходимости подключите собственный OpenRouter или Custom-провайдер.">
      <div className="ai-create-field-offset">
        <SelectField
          label="Режим AI"
          value={credentialMode}
          onChange={(value) => setCredentialMode(value as CredentialMode)}
          options={CREDENTIAL_MODE_OPTIONS}
        />
        {credentialMode === "BYOK" && (
          <SelectField
            label="Интеграция"
            value={providerIntegrationId ? String(providerIntegrationId) : ""}
            onChange={(value) => setProviderIntegrationId(value ? Number(value) : null)}
            options={integrationOptions}
          />
        )}
        <div className="ai-create-help">
          {credentialMode === "CUSTOAI"
            ? "CustoAI использует настроенную платформой модель и лимит организации."
            : "Модель берётся из выбранной OpenRouter или Custom-интеграции."}
        </div>
      </div>
    </CreateAgentStepCard>
  );
}

import { useEffect, useState } from "react";

import { ApiError, api } from "../../api/client";
import { Icon } from "../../shared/icons";
import type { Department, Product } from "../../types";
import { bindConnection, createChannel } from "./api";
import { OPERATOR_POLICY, PRESETS, slugify } from "./model";
import { ChannelWizardAssignmentStep } from "./ChannelWizardAssignmentStep";
import { ChannelWizardChannelStep } from "./ChannelWizardChannelStep";
import { ChannelWizardConnectionsStep, type WizardIntegration } from "./ChannelWizardConnectionsStep";
import type { Channel, PolicyPreset, PolicyViolation } from "./types";

type IntegrationResponse = WizardIntegration & { kind: string; channelId: number | null };
const STEPS = ["Канал", "Назначение", "Подключения"];

export function ChannelCreateWizard({ departments, products, openChannel, openChannels, openAgentCreate }: {
  departments: Department[];
  products: Product[];
  openChannel: (channelId: number) => void;
  openChannels: () => void;
  openAgentCreate: () => void;
}) {
  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [codeTouched, setCodeTouched] = useState(false);
  const [departmentId, setDepartmentId] = useState<number | null>(null);
  const [productId, setProductId] = useState<number | null>(null);
  const [preset, setPreset] = useState<PolicyPreset>("CUSTOM");
  const [created, setCreated] = useState<Channel | null>(null);
  const [integrations, setIntegrations] = useState<WizardIntegration[]>([]);
  const [integrationsFailed, setIntegrationsFailed] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [busyConnectionId, setBusyConnectionId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const effectiveCode = codeTouched ? code : slugify(name);
  const policy = preset === "CUSTOM" ? OPERATOR_POLICY : PRESETS[preset];

  useEffect(() => {
    if (!created) return;
    void api<{ items: IntegrationResponse[] }>("/api/v1/integrations/")
      .then((response) => {
        setIntegrations(response.items.filter((item) => item.kind === "MESSENGER" && (item.channelId === null || item.channelId === created.id)));
        setIntegrationsFailed(false);
      })
      .catch(() => setIntegrationsFailed(true));
  }, [created?.id]);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const response = await createChannel({ code: effectiveCode, name: name.trim(), departmentId, productId, policyPreset: preset, policy: preset === "CUSTOM" ? OPERATOR_POLICY : undefined });
      setCreated(response.channel);
      setStep(2);
    } catch (submitError) {
      if (submitError instanceof ApiError) {
        const violations = (submitError.payload as { violations?: PolicyViolation[] }).violations;
        setError(violations?.length ? violations.map((item) => item.detail).join("; ") : submitError.message);
      } else setError("Не удалось создать канал. Попробуйте ещё раз.");
    } finally {
      setBusy(false);
    }
  }

  async function bind(integrationId: number) {
    if (!created) return;
    setBusyConnectionId(integrationId);
    setConnectionError(null);
    try {
      const response = await bindConnection(created.id, integrationId);
      setCreated(response.channel);
    } catch (bindError) {
      setConnectionError(bindError instanceof ApiError ? bindError.message : "Не удалось привязать подключение.");
    } finally {
      setBusyConnectionId(null);
    }
  }

  return (
    <div className="channel-wizard">
      <h1>Создание канала</h1>
      <p className="channel-wizard-lead">Три шага. Настройка агента и знаний в мастер не входит — агент создаётся отдельным действием в разделе AI. Канал создаётся по завершении шага 2.</p>
      <div className="channel-stepper">
        {STEPS.map((label, index) => (
          <div className={`channel-step ${index < step || created ? "is-done" : ""} ${index === step && !created ? "is-current" : ""}`} key={label}>
            <span>{index < step || created ? <Icon name="check" size={14} /> : index + 1}</span>{label}
          </div>
        ))}
      </div>
      {error && <div className="channel-feedback is-error">{error}</div>}
      {step === 0 && <ChannelWizardChannelStep name={name} code={effectiveCode} departmentId={departmentId} departments={departments} onNameChange={setName} onCodeChange={(value) => { setCodeTouched(true); setCode(value); }} onDepartmentChange={setDepartmentId} onCancel={openChannels} onNext={() => setStep(1)} />}
      {step === 1 && <ChannelWizardAssignmentStep productId={productId} products={products} preset={preset} policy={policy} busy={busy} onProductChange={setProductId} onPresetChange={setPreset} onBack={() => setStep(0)} onSubmit={() => void submit()} />}
      {step === 2 && created && <ChannelWizardConnectionsStep channel={created} integrations={integrations} loadingFailed={integrationsFailed} connectionError={connectionError} busyId={busyConnectionId} onBind={(id) => void bind(id)} openChannel={openChannel} openChannels={openChannels} openAgentCreate={openAgentCreate} />}
    </div>
  );
}

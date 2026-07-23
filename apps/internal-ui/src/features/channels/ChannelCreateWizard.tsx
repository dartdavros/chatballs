import { useState } from "react";

import { ApiError } from "../../api/client";
import { Icon } from "../../shared/icons";
import { Button } from "../../shared/ui-controls";
import type { Department, Product } from "../../types";
import { createChannel } from "./api";
import { OPERATOR_POLICY, PRESETS, slugify } from "./model";
import { ChannelWizardAssignmentStep } from "./ChannelWizardAssignmentStep";
import { ChannelWizardChannelStep } from "./ChannelWizardChannelStep";
import { ChannelWizardSummary } from "./ChannelWizardSummary";
import type { Channel, PolicyPreset, PolicyViolation } from "./types";

const STEPS = ["Канал", "Назначение"];

export function ChannelCreateWizard({
  departments,
  products,
  openChannel,
  openChannels,
  openAgentCreate,
  openIntegrations,
}: {
  departments: Department[];
  products: Product[];
  openChannel: (channelId: number) => void;
  openChannels: () => void;
  openAgentCreate: () => void;
  openIntegrations: () => void;
}) {
  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [codeTouched, setCodeTouched] = useState(false);
  const [departmentId, setDepartmentId] = useState<number | null>(null);
  const [productId, setProductId] = useState<number | null>(null);
  const [preset, setPreset] = useState<PolicyPreset>("CUSTOM");
  const [created, setCreated] = useState<Channel | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const effectiveCode = codeTouched ? code : slugify(name);
  const policy = preset === "CUSTOM" ? OPERATOR_POLICY : PRESETS[preset];
  const departmentName = departments.find((item) => item.id === departmentId)?.name ?? "Без отдела";
  const productName = products.find((item) => item.id === productId)?.name ?? "— непродуктовый";

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const response = await createChannel({
        code: effectiveCode,
        name: name.trim(),
        departmentId,
        productId,
        policyPreset: preset,
        policy: preset === "CUSTOM" ? OPERATOR_POLICY : undefined,
      });
      setCreated(response.channel);
    } catch (submitError) {
      if (submitError instanceof ApiError) {
        const violations = (submitError.payload as { violations?: PolicyViolation[] }).violations;
        setError(violations?.length
          ? violations.map((item) => item.detail).join("; ")
          : submitError.message);
      } else {
        setError("Не удалось создать канал. Попробуйте ещё раз.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="channel-wizard">
      <h1>Создание канала</h1>
      <p className="channel-wizard-lead">
        Два шага: основные данные и назначение. AI-агент и подключения настраиваются
        отдельно в соответствующих разделах.
      </p>

      <div className="channel-stepper">
        {STEPS.map((label, index) => {
          const done = created !== null || index < step;
          return (
            <div className={`channel-step ${done ? "is-done" : ""} ${index === step && !created ? "is-current" : ""}`} key={label}>
              <span>{done ? <Icon name="check" size={14} /> : index + 1}</span>
              {label}
            </div>
          );
        })}
      </div>

      {error && <div className="channel-feedback is-error">{error}</div>}

      {created ? (
        <div className="channel-wizard-final">
          <section className="channel-card-section channel-wizard-done">
            <span className="channel-wizard-check"><Icon name="check" size={28} /></span>
            <h3>Канал создан</h3>
            <p>
              <b>{created.name}</b> — операторский канал: AI-агента нет, диалоги ведут операторы.
              Подключения настраиваются отдельно в разделе «Интеграции».
            </p>
            <div className="channel-wizard-actions is-centered">
              <Button variant="primary" onClick={() => openChannel(created.id)}>Открыть карточку канала</Button>
              <Button variant="secondary" onClick={openChannels}>К списку каналов</Button>
            </div>
          </section>
          <ChannelWizardSummary
            name={created.name}
            code={created.code}
            departmentName={created.departmentName ?? "Без отдела"}
            productName={created.product?.name ?? "— непродуктовый"}
            showDestinations
            openAgentCreate={openAgentCreate}
            openIntegrations={openIntegrations}
          />
        </div>
      ) : (
        <div className="channel-wizard-grid">
          {step === 0 ? (
            <ChannelWizardChannelStep
              name={name}
              code={effectiveCode}
              departmentId={departmentId}
              departments={departments}
              onNameChange={setName}
              onCodeChange={(value) => {
                setCodeTouched(true);
                setCode(value);
              }}
              onDepartmentChange={setDepartmentId}
              onCancel={openChannels}
              onNext={() => setStep(1)}
            />
          ) : (
            <ChannelWizardAssignmentStep
              productId={productId}
              products={products}
              preset={preset}
              policy={policy}
              busy={busy}
              onProductChange={setProductId}
              onPresetChange={setPreset}
              onBack={() => setStep(0)}
              onSubmit={() => void submit()}
            />
          )}
          <ChannelWizardSummary
            name={name.trim()}
            code={effectiveCode}
            departmentName={departmentName}
            productName={productName}
            openAgentCreate={openAgentCreate}
            openIntegrations={openIntegrations}
          />
        </div>
      )}
    </div>
  );
}

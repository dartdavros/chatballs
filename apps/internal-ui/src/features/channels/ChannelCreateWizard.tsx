import { useEffect, useMemo, useState } from "react";

import { ApiError, api } from "../../api/client";
import { Icon } from "../../shared/icons";
import { Button } from "../../shared/ui-controls";
import type { Department, Product } from "../../types";
import { ChannelBadge, providerLabel } from "./ChannelBadge";
import { bindConnection, createChannel } from "./api";
import { OPERATOR_POLICY, PRESETS, PRESET_LABELS, slugify } from "./model";
import type { Channel, PolicyPreset, PolicyViolation } from "./types";
import "./styles.css";

type Integration = { id: number; kind: string; provider: string; name: string; channelId: number | null };

const STEPS = ["Канал", "Назначение", "Подключения"];

export function ChannelCreateWizard({
  departments,
  products,
  openChannel,
  openChannels,
  openAgentCreate,
}: {
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
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const effectiveCode = codeTouched ? code : slugify(name);

  useEffect(() => {
    if (step !== 2) return;
    void api<{ items: Integration[] }>("/api/v1/integrations/")
      .then((response) =>
        setIntegrations(response.items.filter((item) => item.kind === "MESSENGER")),
      )
      .catch(() => setIntegrations([]));
  }, [step]);

  // SALES и SUPPORT требуют продукта — иначе нарушают P1-P3.
  const presetNeedsProduct = preset === "SALES" || preset === "SUPPORT";
  const canSubmit = Boolean(name.trim() && effectiveCode) && (!presetNeedsProduct || productId !== null);

  const policySummary = useMemo(() => {
    if (preset === "CUSTOM") return OPERATOR_POLICY;
    return PRESETS[preset];
  }, [preset]);

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
      setStep(2);
    } catch (submitError) {
      if (submitError instanceof ApiError) {
        const violations = (submitError.payload as { violations?: PolicyViolation[] }).violations;
        setError(
          violations?.length
            ? violations.map((item) => `${item.detail} (${item.rule})`).join("; ")
            : submitError.message,
        );
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="channel-wizard">
      <h1>Создание канала</h1>
      <p className="channel-wizard-lead">
        Три шага. Настройка агента и знаний в мастер не входит — агент создаётся отдельным
        действием в разделе AI. Канал создаётся по завершении шага 2.
      </p>

      <div className="channel-stepper">
        {STEPS.map((label, index) => (
          <div className={`channel-step ${index <= step ? "is-done" : ""}`} key={label}>
            <span>{index < step || created ? <Icon name="check" size={14} /> : index + 1}</span>
            {label}
          </div>
        ))}
      </div>

      {error && <div className="channel-feedback is-error">{error}</div>}

      {step === 0 && (
        <section className="channel-card-section">
          <header>
            <h3>Канал</h3>
          </header>
          <div className="channel-wizard-fields">
            <label>
              <span>Название</span>
              <input value={name} onChange={(event) => setName(event.target.value)} placeholder="Партнёрская линия" />
            </label>
            <label>
              <span>Код</span>
              <input
                value={effectiveCode}
                onChange={(event) => {
                  setCodeTouched(true);
                  setCode(event.target.value);
                }}
                placeholder="partners"
              />
              <em>Входит в embed-URL виджета и не меняется после создания.</em>
            </label>
            <label>
              <span>Отдел</span>
              <select
                value={departmentId ?? ""}
                onChange={(event) => setDepartmentId(event.target.value ? Number(event.target.value) : null)}
              >
                <option value="">Без отдела</option>
                {departments.map((department) => (
                  <option value={department.id} key={department.id}>{department.name}</option>
                ))}
              </select>
            </label>
          </div>
          <div className="channel-wizard-actions">
            <Button variant="secondary" onClick={openChannels}>Отмена</Button>
            <Button variant="primary" disabled={!name.trim() || !effectiveCode} onClick={() => setStep(1)}>
              Далее
            </Button>
          </div>
        </section>
      )}

      {step === 1 && (
        <section className="channel-card-section">
          <header>
            <h3>Назначение</h3>
          </header>
          <div className="channel-wizard-fields">
            <label>
              <span>Продукт</span>
              <select
                value={productId ?? ""}
                onChange={(event) => setProductId(event.target.value ? Number(event.target.value) : null)}
              >
                <option value="">— непродуктовый</option>
                {products.map((product) => (
                  <option value={product.id} key={product.id}>{product.name}</option>
                ))}
              </select>
            </label>
            <label>
              <span>Пресет политики</span>
              <select value={preset} onChange={(event) => setPreset(event.target.value as PolicyPreset)}>
                {(["SALES", "SUPPORT", "CUSTOM"] as PolicyPreset[]).map((item) => (
                  <option value={item} key={item}>{PRESET_LABELS[item]}</option>
                ))}
              </select>
              {presetNeedsProduct && productId === null && (
                <em className="is-warning">
                  Пресет «{PRESET_LABELS[preset]}» требует продукта — иначе нарушаются инварианты P1–P3.
                </em>
              )}
            </label>
          </div>
          <div className="channel-wizard-policy">
            {Object.entries(policySummary).map(([flag, value]) => (
              <span key={flag} className={value ? "is-on" : ""}>{flag}</span>
            ))}
          </div>
          <div className="channel-wizard-actions">
            <Button variant="secondary" onClick={() => setStep(0)}>Назад</Button>
            <Button variant="primary" disabled={!canSubmit || busy} onClick={submit}>
              Создать канал
            </Button>
          </div>
        </section>
      )}

      {step === 2 && created && (
        <div className="channel-wizard-final">
          <section className="channel-card-section">
            <header>
              <h3>Подключения</h3>
              <span>Шаг можно пропустить</span>
            </header>
            {integrations.length === 0 ? (
              <p className="channel-muted">Свободных подключений нет — их можно привязать позже в карточке канала.</p>
            ) : (
              <div className="channel-connections">
                {integrations.map((integration) => {
                  const bound = created.connections.some((item) => item.id === integration.id);
                  return (
                    <div className="channel-connection" key={integration.id}>
                      <ChannelBadge provider={integration.provider} />
                      <div className="channel-connection-text">
                        <strong>{integration.name}</strong>
                        <span>{providerLabel(integration.provider)}</span>
                      </div>
                      <Button
                        variant="secondary"
                        disabled={bound}
                        onClick={async () => {
                          const response = await bindConnection(created.id, integration.id);
                          setCreated(response.channel);
                        }}
                      >
                        {bound ? "Привязано" : "Привязать"}
                      </Button>
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          <section className="channel-card-section channel-wizard-done">
            <span className="channel-wizard-check"><Icon name="check" size={28} /></span>
            <strong>Канал создан</strong>
            <p>
              <b>{created.name}</b> — операторский канал: AI-агента нет, диалоги ведут операторы.
              Канал принимает подключения, диалоги, заказы и attribution.
            </p>
            <div className="channel-wizard-actions is-centered">
              <Button variant="primary" onClick={() => openChannel(created.id)}>
                Открыть карточку канала
              </Button>
              <Button variant="secondary" onClick={openChannels}>К списку каналов</Button>
            </div>
            <a
              href="#"
              className="channel-wizard-agent-hint"
              onClick={(event) => {
                event.preventDefault();
                openAgentCreate();
              }}
            >
              Нужен AI-агент? Создайте его в разделе AI
              <Icon name="arrow" size={14} />
            </a>
          </section>
        </div>
      )}
    </div>
  );
}

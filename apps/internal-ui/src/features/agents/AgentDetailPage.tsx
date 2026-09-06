import { Modal } from "antd";
import { useCallback, useEffect, useState } from "react";

import { ApiError } from "../../api/client";
import { ChannelBadge } from "../../shared/badges";
import { FormField, KeyValue, SelectField, TextAreaField } from "../../shared/form-controls";
import { Icon } from "../../shared/icons";
import { providerLabel } from "../../shared/providers";
import { EmptyState, ErrorScreen, LoadingState, StatusPill } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
import { formatDate } from "../../shared/utils";
import type { EmployeeGroup, RouteKey } from "../../types";
import { api } from "../../api/client";
import { fetchLlmProviders, type Integration } from "../integrations/model";
import { connectionStatus } from "./connection-status";
import {
  bindAgentConnection,
  deleteAgent,
  fetchAgent,
  patchAgent,
  setAgentAiActive,
  unbindAgentConnection,
  type AgentCard,
  type AgentPatch,
} from "./model";

type Feedback = { kind: "error" | "warning"; text: string } | null;

function useAgentCard(agentId: number | null) {
  const [card, setCard] = useState<AgentCard | null>(null);
  const [missing, setMissing] = useState(false);
  const [failed, setFailed] = useState(false);

  const load = useCallback(async () => {
    if (!agentId) {
      setMissing(true);
      return;
    }
    try {
      const payload = await fetchAgent(agentId);
      setCard(payload.agent);
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 404) setMissing(true);
      else setFailed(true);
    }
  }, [agentId]);

  useEffect(() => {
    void load();
  }, [load]);

  return { card, setCard, missing, failed, reload: load };
}

export function AgentDetailPage({
  agentId,
  groups,
  canManage,
  canManageConnections,
  openAgents,
  openKnowledge,
  openIntegrations,
  setRoute,
  onLoaded,
}: {
  agentId: number | null;
  groups: EmployeeGroup[];
  canManage: boolean;
  canManageConnections: boolean;
  openAgents: () => void;
  openKnowledge: (knowledgeId: number) => void;
  openIntegrations: () => void;
  setRoute: (route: RouteKey) => void;
  onLoaded: (name: string | null) => void;
}) {
  const { card, setCard, missing, failed, reload } = useAgentCard(agentId);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<Feedback>(null);
  const [deleting, setDeleting] = useState(false);
  const [providers, setProviders] = useState<Integration[]>([]);
  const [messengers, setMessengers] = useState<Integration[]>([]);

  const loadMessengers = useCallback(async () => {
    try {
      const payload = await api<{ items: Integration[] }>("/api/v1/integrations/");
      setMessengers(payload.items.filter((item) => item.kind === "MESSENGER" && !item.config.purpose));
    } catch {
      setMessengers([]);
    }
  }, []);

  useEffect(() => {
    onLoaded(card?.name ?? null);
    return () => onLoaded(null);
  }, [card?.name, onLoaded]);

  useEffect(() => {
    if (canManage) fetchLlmProviders().then(setProviders).catch(() => setProviders([]));
  }, [canManage]);

  useEffect(() => {
    if (canManageConnections) void loadMessengers();
  }, [canManageConnections, loadMessengers]);

  if (missing) return <EmptyState title="Агент не найден" />;
  if (failed) return <ErrorScreen retry={() => void reload()} />;
  if (!card) return <LoadingState />;

  async function apply(patch: AgentPatch) {
    setBusy(true);
    setFeedback(null);
    try {
      const saved = await patchAgent(card!.id, patch);
      setCard(saved.agent);
      return true;
    } catch (caught) {
      setFeedback({
        kind: "error",
        text: caught instanceof ApiError ? caught.payload.detail ?? "Не удалось сохранить" : "Не удалось сохранить",
      });
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function toggleAi() {
    setBusy(true);
    setFeedback(null);
    try {
      const saved = await setAgentAiActive(card!.id, card!.aiStatus !== "ACTIVE");
      setCard(saved.agent);
    } catch (caught) {
      setFeedback({
        kind: "error",
        text: caught instanceof ApiError && caught.payload.detail
          ? caught.payload.detail
          : "Не удалось изменить статус AI",
      });
    } finally {
      setBusy(false);
    }
  }

  async function removeAgent() {
    setBusy(true);
    try {
      await deleteAgent(card!.id);
      openAgents();
    } catch (caught) {
      setDeleting(false);
      setFeedback({
        kind: "warning",
        text:
          caught instanceof ApiError && caught.status === 409
            ? "Агента нельзя удалить: есть диалоги или подключения. Отвяжите подключения и закройте диалоги."
            : "Не удалось удалить агента",
      });
    } finally {
      setBusy(false);
    }
  }

  async function unbind(integrationId: number) {
    setBusy(true);
    try {
      const saved = await unbindAgentConnection(card!.id, integrationId);
      setCard(saved.agent);
      void loadMessengers();
    } catch {
      setFeedback({ kind: "error", text: "Не удалось отвязать подключение" });
    } finally {
      setBusy(false);
    }
  }

  async function bind(integrationId: number) {
    setBusy(true);
    setFeedback(null);
    try {
      const saved = await bindAgentConnection(card!.id, integrationId);
      setCard(saved.agent);
      void loadMessengers();
    } catch (caught) {
      setFeedback({
        kind: "error",
        text:
          caught instanceof ApiError && caught.status === 409
            ? "Подключение уже привязано к другому агенту"
            : "Не удалось привязать подключение",
      });
    } finally {
      setBusy(false);
    }
  }

  const status = card.aiStatus === "ACTIVE" ? "active" : card.aiStatus === "DRAFT" ? "draft" : "disabled";

  return (
    <div className="agent-detail">
      <header className="agent-detail-header">
        <div>
          <div className="agent-detail-title">
            <h1>{card.name}</h1>
            <StatusPill status={card.isActive ? status : "archived"} />
          </div>
          <div className="agent-detail-meta">
            <span>{card.groupName ?? "Без группы"}</span>
            <span>·</span>
            <code>{card.code}</code>
          </div>
        </div>
        {canManage && (
          <div className="agent-detail-actions">
            <Button variant="secondary" icon={card.aiStatus === "ACTIVE" ? "pause" : "bolt"} disabled={busy} onClick={() => void toggleAi()}>
              {card.aiStatus === "ACTIVE" ? "Остановить AI" : "Запустить AI"}
            </Button>
          </div>
        )}
      </header>

      {feedback && <div className={`agent-feedback is-${feedback.kind}`}>{feedback.text}</div>}

      <AssignmentSection card={card} groups={groups} canManage={canManage} busy={busy} apply={apply} />
      <InstructionsSection card={card} canManage={canManage} busy={busy} apply={apply} />
      <ModelSection card={card} providers={providers} canManage={canManage} busy={busy} apply={apply} />
      <KnowledgeSection card={card} openKnowledge={openKnowledge} setRoute={setRoute} />
      <ConnectionsSection
        card={card}
        canManage={canManageConnections}
        busy={busy}
        available={messengers.filter((item) => item.channel === null)}
        openIntegrations={openIntegrations}
        bind={bind}
        unbind={unbind}
      />

      {canManage && (
        <footer className="agent-danger-actions">
          <Button
            variant="secondary"
            icon="pause"
            disabled={busy}
            onClick={() => void apply({ isActive: !card.isActive })}
          >
            {card.isActive ? "Выключить агента" : "Включить агента"}
          </Button>
          <Button variant="danger-outline" icon="trash" disabled={busy} onClick={() => setDeleting(true)}>
            Удалить
          </Button>
        </footer>
      )}

      {deleting && (
        <Modal
          open
          title="Удалить агента?"
          okText="Удалить"
          cancelText="Отмена"
          okButtonProps={{ danger: true, disabled: busy }}
          onOk={() => void removeAgent()}
          onCancel={() => setDeleting(false)}
        >
          <p>Агент «{card.name}» будет удалён безвозвратно. Диалоги и подключения не дают удалить агента.</p>
        </Modal>
      )}
    </div>
  );
}

function AssignmentSection({
  card, groups, canManage, busy, apply,
}: {
  card: AgentCard;
  groups: EmployeeGroup[];
  canManage: boolean;
  busy: boolean;
  apply: (patch: AgentPatch) => Promise<boolean>;
}) {
  const [name, setName] = useState(card.name);
  useEffect(() => setName(card.name), [card.name]);
  const dirty = name.trim() !== card.name && name.trim().length > 0;

  return (
    <section className="agent-card-section">
      <header>
        <h3>Назначение</h3>
        <span>Группа определяет, какие сотрудники видят диалоги агента; без группы диалоги видны всем</span>
      </header>
      <div className="agent-assignment">
        {canManage ? (
          <FormField label="Название" value={name} onChange={setName} />
        ) : (
          <KeyValue label="Название" value={card.name} />
        )}
        {canManage ? (
          <SelectField
            label="Группа"
            value={card.groupId === null ? "" : String(card.groupId)}
            onChange={(value) => void apply({ groupId: value ? Number(value) : null })}
            options={[["", "Без группы"], ...groups.map((item) => [String(item.id), item.name] as [string, string])]}
          />
        ) : (
          <KeyValue label="Группа" value={card.groupName ?? "Без группы"} />
        )}
        <KeyValue label="Код" value={<code>{card.code}</code>} />
        <KeyValue label="Создан" value={formatDate(card.createdAt)} />
      </div>
      {canManage && dirty && (
        <div className="agent-section-actions">
          <Button variant="secondary" disabled={busy} onClick={() => setName(card.name)}>Отменить</Button>
          <Button variant="primary" disabled={busy} onClick={() => void apply({ name: name.trim() })}>Сохранить</Button>
        </div>
      )}
    </section>
  );
}

function InstructionsSection({
  card, canManage, busy, apply,
}: {
  card: AgentCard;
  canManage: boolean;
  busy: boolean;
  apply: (patch: AgentPatch) => Promise<boolean>;
}) {
  const [persona, setPersona] = useState(card.persona);
  const [tone, setTone] = useState(card.tone);
  const [instructions, setInstructions] = useState(card.instructions);
  useEffect(() => {
    setPersona(card.persona);
    setTone(card.tone);
    setInstructions(card.instructions);
  }, [card.persona, card.tone, card.instructions]);
  const dirty = persona !== card.persona || tone !== card.tone || instructions !== card.instructions;

  if (!canManage) {
    return (
      <section className="agent-card-section">
        <header><h3>Инструкции</h3></header>
        {card.persona || card.tone || card.instructions ? (
          <div className="agent-instructions-grid">
            {card.persona && <KeyValue label="Кто он" value={card.persona} />}
            {card.tone && <KeyValue label="Как говорит" value={card.tone} />}
            {card.instructions && <KeyValue label="Правила" value={card.instructions} />}
          </div>
        ) : (
          <p className="agent-muted">Инструкции не заданы.</p>
        )}
      </section>
    );
  }

  return (
    <section className="agent-card-section">
      <header>
        <h3>Инструкции</h3>
        <span>Системный промпт собирается из трёх частей в этом порядке</span>
      </header>
      <div className="agent-instructions-grid">
        <TextAreaField label="Кто он и что делает" value={persona} onChange={setPersona} />
        <TextAreaField label="Как он должен говорить" value={tone} onChange={setTone} />
        <TextAreaField label="Правила работы" value={instructions} onChange={setInstructions} />
      </div>
      {dirty && (
        <div className="agent-section-actions">
          <Button variant="secondary" disabled={busy} onClick={() => { setPersona(card.persona); setTone(card.tone); setInstructions(card.instructions); }}>
            Отменить
          </Button>
          <Button variant="primary" disabled={busy} onClick={() => void apply({ persona, tone, instructions })}>
            Сохранить
          </Button>
        </div>
      )}
    </section>
  );
}

function ModelSection({
  card, providers, canManage, busy, apply,
}: {
  card: AgentCard;
  providers: Integration[];
  canManage: boolean;
  busy: boolean;
  apply: (patch: AgentPatch) => Promise<boolean>;
}) {
  return (
    <section className="agent-card-section">
      <header>
        <h3>Модель и провайдер</h3>
        <span>AI отвечает через провайдера вашей организации — ключ добавляется в «Настройках», раздел «AI-провайдер»</span>
      </header>
      <div className="agent-assignment">
        <KeyValue label="Модель" value={<code>{card.model}</code>} />
        {canManage ? (
          <SelectField
            label="Провайдер"
            value={card.providerIntegrationId ? String(card.providerIntegrationId) : ""}
            onChange={(value) => void apply({ providerIntegrationId: value ? Number(value) : null })}
            options={[["", "Не выбран"], ...providers.map((item) => [String(item.id), item.name] as [string, string])]}
          />
        ) : (
          <KeyValue
            label="Провайдер"
            value={card.providerIntegrationId === null
              ? "Не выбран"
              : providers.find((item) => item.id === card.providerIntegrationId)?.name ?? String(card.providerIntegrationId)}
          />
        )}
      </div>
      {busy && <p className="agent-muted">Сохранение…</p>}
    </section>
  );
}

function KnowledgeSection({
  card, openKnowledge, setRoute,
}: {
  card: AgentCard;
  openKnowledge: (knowledgeId: number) => void;
  setRoute: (route: RouteKey) => void;
}) {
  const total = card.knowledge.length + card.portalArticles.length;
  return (
    <section className="agent-card-section">
      <header>
        <h3>Знания</h3>
        <button className="link has-icon" type="button" onClick={() => setRoute("aiKnowledge")}>
          Перейти в знания
          <Icon name="arrow" size={14} />
        </button>
      </header>
      {total === 0 ? (
        <p className="agent-muted">Знания не прикреплены — выберите их в разделе «Знания» или статьи на портале поддержки.</p>
      ) : (
        <>
          {card.knowledge.length > 0 && (
            <ul className="agent-knowledge-list is-readonly">
              {card.knowledge.map((item) => (
                <li key={item.id}>
                  <button className="link is-strong is-neutral agent-knowledge-text" type="button" onClick={() => openKnowledge(item.id)}>
                    {item.title}
                  </button>
                  {!item.isEnabled && <span className="ai-doc-chip off">Выключено</span>}
                </li>
              ))}
            </ul>
          )}
          {card.portalArticles.length > 0 && (
            <ul className="agent-knowledge-list is-readonly">
              {card.portalArticles.map((article) => (
                <li key={article.id}>
                  <a className="link is-strong is-neutral agent-knowledge-text" href={article.publicUrl} rel="noreferrer" target="_blank">
                    {article.title}
                  </a>
                  <span className="ai-doc-chip plain">{article.portal.name}</span>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}

function ConnectionsSection({
  card, canManage, busy, available, openIntegrations, bind, unbind,
}: {
  card: AgentCard;
  canManage: boolean;
  busy: boolean;
  available: Integration[];
  openIntegrations: () => void;
  bind: (integrationId: number) => void;
  unbind: (integrationId: number) => void;
}) {
  return (
    <section className="agent-card-section">
      <header>
        <h3>Подключения</h3>
        {canManage && (
          <button className="link has-icon" type="button" onClick={openIntegrations}>
            Открыть настройки
            <Icon name="arrow" size={14} />
          </button>
        )}
      </header>
      {card.connections.length === 0 ? (
        <p className="agent-muted">Подключений нет. Добавьте бота, почту или веб-виджет в «Настройках», раздел «Интеграции», и привяжите к агенту.</p>
      ) : (
        <div className="agent-connections">
          {card.connections.map((connection) => (
            <div className="agent-connection" key={connection.id}>
              <ChannelBadge provider={connection.provider} />
              <div className="agent-connection-text">
                <strong>{connection.name}</strong>
                <span>{providerLabel(connection.provider)}</span>
              </div>
              <StatusPill status={connectionStatus(connection.status)} />
              {canManage && (
                <Button variant="secondary" disabled={busy} onClick={() => unbind(connection.id)}>Отвязать</Button>
              )}
            </div>
          ))}
        </div>
      )}
      {canManage && available.length > 0 && (
        <div className="agent-connections" style={{ marginTop: 8 }}>
          {available.map((integration) => (
            <div className="agent-connection" key={integration.id}>
              <ChannelBadge provider={integration.provider} />
              <div className="agent-connection-text">
                <strong>{integration.name}</strong>
                <span>Свободное подключение</span>
              </div>
              <Button variant="secondary" disabled={busy} onClick={() => bind(integration.id)}>Привязать</Button>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

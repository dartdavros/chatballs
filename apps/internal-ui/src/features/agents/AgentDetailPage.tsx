import { Dropdown, Modal } from "antd";
import { useCallback, useEffect, useState } from "react";

import { api, ApiError } from "../../api/client";
import { ChannelGlyph } from "../../shared/badges";
import { Icon } from "../../shared/icons";
import { EmptyState, ErrorScreen, LoadingState } from "../../shared/ui";
import { BackLink, Button, CopyButton } from "../../shared/ui-controls";
import type { EmployeeGroup, RouteKey } from "../../types";
import { groupColorOf } from "../conversations/model";
import { linkKnowledgeToAgent, linkPortalArticlesToAgent } from "../ai/knowledge/api";
import { fetchLlmProviders, webWidgetSnippet, type Integration } from "../integrations/model";
import { AgentKnowledgeDialog } from "./AgentKnowledgeDialog";
import {
  agentStatusMeta,
  agentTile,
  agentTint,
  bindAgentConnection,
  connectionStatusMeta,
  connectionSubtitle,
  createdLabel,
  dailyCostCents,
  dailyCostInput,
  deleteAgent,
  fetchAgent,
  knowledgeLine,
  knowledgeRows,
  openDialogsLine,
  patchAgent,
  setAgentAiActive,
  unbindAgentConnection,
  type AgentCard,
  type AgentConnection,
  type AgentPatch,
} from "./model";

// Карточка агента (дизайн-базлайн v2, «Агенты Baseline», кадры G3–G5): слева —
// что агент знает и как говорит (инструкции, знания), справа — как он работает
// (назначение, подключения, модель). Изменения применяются сразу (ADR-HUB-0023).

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
  openAiProvider,
  onLoaded,
}: {
  agentId: number | null;
  groups: EmployeeGroup[];
  canManage: boolean;
  canManageConnections: boolean;
  openAgents: () => void;
  openKnowledge: (knowledgeId: number) => void;
  openIntegrations: () => void;
  openAiProvider: () => void;
  setRoute: (route: RouteKey) => void;
  onLoaded: (name: string | null) => void;
}) {
  const { card, setCard, missing, failed, reload } = useAgentCard(agentId);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<Feedback>(null);
  const [deleting, setDeleting] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
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

  const tile = agentTile(card);
  const status = agentStatusMeta(card);
  const running = card.aiStatus === "ACTIVE";
  // Выключение агента и удаление живут в этом меню, а не отдельными кнопками
  // под карточкой: на странице остаётся один переключатель AI.
  const menuItems = [
    { key: "copy-code", label: <button type="button" onClick={() => { setMenuOpen(false); void navigator.clipboard?.writeText(card.code); }}><Icon name="copy" size={15} />Скопировать код</button> },
    { type: "divider" as const },
    {
      key: "active",
      disabled: busy,
      label: (
        <button type="button" onClick={() => { setMenuOpen(false); void apply({ isActive: !card.isActive }); }}>
          <Icon name={card.isActive ? "xCircle" : "check"} size={15} />{card.isActive ? "Выключить агента" : "Включить агента"}
        </button>
      ),
    },
    {
      key: "delete",
      disabled: busy,
      label: (
        <button className="danger" type="button" onClick={() => { setMenuOpen(false); setDeleting(true); }}>
          <Icon name="trash" size={15} />Удалить агента
        </button>
      ),
    },
  ];

  return (
    <div className="agent-page">
      <BackLink label="Агенты" onClick={openAgents} />

      <header className="agent-head">
        <span className="agent-head-tile" style={{ background: tile.background, color: tile.color }}>
          <Icon name="robot" size={28} strokeWidth={1.8} />
        </span>
        <div className="agent-head-text">
          <div>
            <h2>{card.name}</h2>
            <b className="agents-status" style={{ background: status.bg, color: status.color }}><i />{status.text}</b>
          </div>
          <p>
            <span><i style={{ background: card.groupId === null ? "var(--n-5)" : groupColorOf(card.groupId, card.groupColor) }} />{card.groupName ?? "Без группы"}</span>
            <i />
            <code>{card.code}</code>
            <i />
            {openDialogsLine(card.counters.openConversations)}
            <i />
            создан {createdLabel(card.createdAt)}
          </p>
        </div>
        {canManage && (
          <div className="agent-head-actions">
            <Button variant="secondary" className="agent-toggle" icon={running ? "pause" : "bolt"} disabled={busy} onClick={() => void toggleAi()}>
              {running ? "Остановить AI" : "Запустить AI"}
            </Button>
            <Dropdown menu={{ items: menuItems }} open={menuOpen} onOpenChange={setMenuOpen} trigger={["click"]} overlayClassName="app-dropdown">
              <button className="agent-head-menu" type="button" aria-label="Действия агента" title="Действия"><Icon name="more" size={17} strokeWidth={2} /></button>
            </Dropdown>
          </div>
        )}
      </header>

      {card.providerIntegrationId === null && (
        <div className="agent-blocker">
          <Icon name="alert" size={18} strokeWidth={2.2} />
          <div>
            <strong>AI не может отвечать: провайдер не выбран</strong>
            <small>Добавьте ключ в «Настройки → AI-провайдер» и выберите провайдера в блоке «Модель». До этого диалоги агента ждут человека.</small>
          </div>
          {canManage && (
            <button type="button" onClick={openAiProvider}>Открыть настройки<Icon name="external" size={13} strokeWidth={2.2} /></button>
          )}
        </div>
      )}

      {feedback && <div className={`agent-feedback is-${feedback.kind}`}>{feedback.text}</div>}

      <div className="agent-grid">
        <div className="agent-column">
          <InstructionsCard card={card} canManage={canManage} busy={busy} apply={apply} />
          <KnowledgeCard card={card} canManage={canManage} openKnowledge={openKnowledge} reload={reload} />
        </div>
        <div className="agent-column">
          <AssignmentCard card={card} groups={groups} canManage={canManage} busy={busy} apply={apply} />
          <ConnectionsCard
            card={card}
            canManage={canManageConnections}
            busy={busy}
            available={messengers.filter((item) => item.channel === null)}
            openIntegrations={openIntegrations}
            bind={bind}
            unbind={unbind}
          />
          <ModelCard card={card} providers={providers} canManage={canManage} busy={busy} apply={apply} />
        </div>
      </div>

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

// --- Инструкции (кадры G3/G5) ---

const INSTRUCTION_FIELDS = [
  { key: "persona", label: "Кто он и что делает", hint: "персонализация", rows: 7, placeholder: "" },
  { key: "tone", label: "Как он должен говорить", hint: "тон", rows: 7, placeholder: "Например: спокойно и вежливо, на «вы»" },
  { key: "instructions", label: "Правила работы", hint: "инструкции", rows: 10, placeholder: "Например: не называй цены, направляй к консультанту" },
] as const;

function InstructionsCard({ card, canManage, busy, apply }: {
  card: AgentCard;
  canManage: boolean;
  busy: boolean;
  apply: (patch: AgentPatch) => Promise<boolean>;
}) {
  const [draft, setDraft] = useState({ persona: card.persona, tone: card.tone, instructions: card.instructions });
  useEffect(() => {
    setDraft({ persona: card.persona, tone: card.tone, instructions: card.instructions });
  }, [card.persona, card.tone, card.instructions]);
  const dirty = draft.persona !== card.persona || draft.tone !== card.tone || draft.instructions !== card.instructions;

  return (
    <section className="agent-card">
      <div className="agent-card-head">
        <h3>Инструкции</h3>
        <small>Системный промпт собирается из трёх частей в этом порядке</small>
      </div>
      <div className="agent-instructions">
        {INSTRUCTION_FIELDS.map((field) => (
          <label className={`agent-field is-text is-rows-${field.rows}`} key={field.key}>
            <span>{field.label}<small>{field.hint}</small></span>
            {canManage ? (
              <textarea
                value={draft[field.key]}
                placeholder={field.placeholder}
                onChange={(event) => setDraft((current) => ({ ...current, [field.key]: event.target.value }))}
              />
            ) : (
              <span className="agent-field-static">{card[field.key] || "—"}</span>
            )}
          </label>
        ))}
      </div>
      {canManage && dirty && (
        <div className="agent-dirty">
          <small>Есть несохранённые изменения — применятся в runtime сразу</small>
          <button type="button" disabled={busy} onClick={() => setDraft({ persona: card.persona, tone: card.tone, instructions: card.instructions })}>Отменить</button>
          <button className="is-primary" type="button" disabled={busy} onClick={() => void apply(draft)}>Сохранить</button>
        </div>
      )}
    </section>
  );
}

// --- Знания (кадры G3/G4/G5) ---

function KnowledgeCard({ card, canManage, openKnowledge, reload }: {
  card: AgentCard;
  canManage: boolean;
  openKnowledge: (knowledgeId: number) => void;
  reload: () => void;
}) {
  const [picking, setPicking] = useState(false);
  const rows = knowledgeRows(card);

  async function detach(kind: "knowledge" | "article", id: number) {
    if (kind === "knowledge") await linkKnowledgeToAgent({ agentId: card.aiAgentId, action: "detach", knowledgeIds: [id] });
    else await linkPortalArticlesToAgent({ agentId: card.aiAgentId, action: "detach", articleIds: [id] });
    reload();
  }

  return (
    <section className="agent-card">
      <div className="agent-card-head is-row">
        <div><h3>Знания</h3><small>{knowledgeLine(card)}</small></div>
        {canManage && (
          <button className="agent-inline-button" type="button" onClick={() => setPicking(true)}>
            <Icon name="plus" size={13} strokeWidth={2.2} />Выбрать
          </button>
        )}
      </div>
      {rows.length === 0 ? (
        <p className="agent-knowledge-empty">Знания не прикреплены — агент отвечает только по инструкциям. Выберите статьи из библиотеки или портала поддержки.</p>
      ) : (
        <div className="agent-knowledge-list">
          {rows.map((row) => (
            <div className="agent-knowledge-row" key={row.key}>
              <Icon name={row.icon} size={15} strokeWidth={1.9} />
              {row.kind === "knowledge"
                ? <button className="agent-knowledge-title" type="button" onClick={() => openKnowledge(row.id)}>{row.title}</button>
                : <a className="agent-knowledge-title" href={row.href} rel="noreferrer" target="_blank">{row.title}</a>}
              {row.chip && <small className={`agent-chip is-${row.chipTone}`}>{row.chip}</small>}
              <small className="agent-knowledge-meta">{row.meta}</small>
              {canManage && (
                <button className="agent-knowledge-remove" type="button" aria-label="Убрать" title="Убрать" onClick={() => void detach(row.kind, row.id)}>
                  <Icon name="close" size={12} strokeWidth={2.4} />
                </button>
              )}
            </div>
          ))}
        </div>
      )}
      {picking && (
        <AgentKnowledgeDialog
          card={card}
          onClose={() => setPicking(false)}
          onSave={async ({ knowledgeIds, articleIds }) => {
            await patchAgent(card.id, { knowledgeIds });
            const current = card.portalArticles.map((article) => article.id);
            const attach = articleIds.filter((id) => !current.includes(id));
            const detachIds = current.filter((id) => !articleIds.includes(id));
            if (attach.length) await linkPortalArticlesToAgent({ agentId: card.aiAgentId, action: "attach", articleIds: attach });
            if (detachIds.length) await linkPortalArticlesToAgent({ agentId: card.aiAgentId, action: "detach", articleIds: detachIds });
            reload();
          }}
        />
      )}
    </section>
  );
}

// --- Назначение (кадры G3–G5) ---

function AssignmentCard({ card, groups, canManage, busy, apply }: {
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
    <section className="agent-card is-side">
      <h3>Назначение</h3>
      <p>Группа определяет, кто из сотрудников видит диалоги агента; без группы — видны всем.</p>
      <div className="agent-side-fields">
        <label className="agent-field">
          <span>Название</span>
          {canManage
            ? <input value={name} onChange={(event) => setName(event.target.value)} onBlur={() => { if (dirty) void apply({ name: name.trim() }); }} />
            : <span className="agent-field-static">{card.name}</span>}
        </label>
        <label className="agent-field is-select">
          <span>Группа</span>
          <span className="agent-field-control">
            <i className="agent-group-dot" style={{ background: card.groupId === null ? "var(--n-5)" : groupColorOf(card.groupId, card.groupColor) }} />
            {canManage ? (
              <select
                disabled={busy}
                value={card.groupId === null ? "" : String(card.groupId)}
                onChange={(event) => void apply({ groupId: event.target.value ? Number(event.target.value) : null })}
              >
                <option value="">Без группы</option>
                {groups.map((group) => <option value={String(group.id)} key={group.id}>{group.name}</option>)}
              </select>
            ) : (
              <span className="agent-field-static">{card.groupName ?? "Без группы"}</span>
            )}
            <Icon name="chevron" size={14} strokeWidth={2.2} />
          </span>
        </label>
      </div>
    </section>
  );
}

// --- Модель (кадры G3–G5) ---

function ModelCard({ card, providers, canManage, busy, apply }: {
  card: AgentCard;
  providers: Integration[];
  canManage: boolean;
  busy: boolean;
  apply: (patch: AgentPatch) => Promise<boolean>;
}) {
  const [limit, setLimit] = useState(dailyCostInput(card.limits));
  useEffect(() => setLimit(dailyCostInput(card.limits)), [card.limits]);
  const missingProvider = card.providerIntegrationId === null;
  const providerName = providers.find((item) => item.id === card.providerIntegrationId)?.name ?? "";

  function saveLimit() {
    const cents = dailyCostCents(limit);
    if (cents === Number(card.limits.dailyCostUsd ?? 0)) return;
    void apply({ limits: { ...card.limits, dailyCostUsd: cents } });
  }

  return (
    <section className="agent-card is-side">
      <h3>Модель</h3>
      <p>Ключ провайдера — в «Настройки → AI-провайдер». Модель выбирается из каталога провайдера.</p>
      <div className="agent-side-fields">
        <label className={`agent-field is-select ${missingProvider ? "is-invalid" : ""}`}>
          <span>Провайдер</span>
          <span className="agent-field-control">
            {canManage ? (
              <select
                disabled={busy}
                value={card.providerIntegrationId ? String(card.providerIntegrationId) : ""}
                onChange={(event) => void apply({ providerIntegrationId: event.target.value ? Number(event.target.value) : null })}
              >
                <option value="">Не выбран</option>
                {providers.map((item) => <option value={String(item.id)} key={item.id}>{item.name}</option>)}
              </select>
            ) : (
              <span className="agent-field-static">{providerName || "Не выбран"}</span>
            )}
            <Icon name="chevron" size={14} strokeWidth={2.2} />
          </span>
        </label>
        <label className="agent-field is-model">
          <span>Модель</span>
          <span className="agent-field-control">
            <span className={`agent-field-static ${missingProvider ? "is-placeholder" : ""}`}>{missingProvider ? "выберите провайдера" : card.model}</span>
            <Icon name="search" size={14} strokeWidth={1.8} />
          </span>
        </label>
        <div className="agent-limit">
          <span>Лимит в день</span>
          <span>
            {canManage
              ? <input value={limit} inputMode="decimal" placeholder="0.00" onChange={(event) => setLimit(event.target.value)} onBlur={saveLimit} />
              : <span className="agent-limit-value">{limit || "0.00"}</span>}
            <small>USD</small>
          </span>
        </div>
      </div>
    </section>
  );
}

// --- Подключения (кадры G3/G4) ---

function ConnectionsCard({ card, canManage, busy, available, openIntegrations, bind, unbind }: {
  card: AgentCard;
  canManage: boolean;
  busy: boolean;
  available: Integration[];
  openIntegrations: () => void;
  bind: (integrationId: number) => void;
  unbind: (integrationId: number) => void;
}) {
  const widget = card.connections.find((connection) => connection.provider === "WEB" && connection.widgetPublicKey);
  return (
    <section className="agent-card is-side">
      <div className="agent-card-head is-tight">
        <h3>Подключения</h3>
        {canManage && (
          <button className="link has-icon" type="button" onClick={openIntegrations}>Интеграции<Icon name="external" size={13} strokeWidth={2.2} /></button>
        )}
      </div>
      <p>Через них клиенты попадают к агенту. Одно подключение — один агент.</p>
      {card.connections.map((connection) => (
        <ConnectionRow
          connection={connection}
          status={connectionStatusMeta(connection.status)}
          action={canManage ? { label: "Отвязать", run: () => unbind(connection.id) } : null}
          busy={busy}
          key={connection.id}
        />
      ))}
      {canManage && available.map((integration) => (
        <ConnectionRow
          connection={{ id: integration.id, provider: integration.provider, name: integration.name, status: integration.status, botUsername: "", email: "", allowedOrigins: [], widgetPublicKey: "" }}
          subtitle="Свободное подключение"
          status={{ text: "Свободно", bg: "var(--n-9)", color: "var(--n-4)" }}
          action={{ label: "Привязать", run: () => bind(integration.id) }}
          busy={busy}
          key={`free-${integration.id}`}
        />
      ))}
      {widget && (
        <div className="agent-widget">
          <div>
            <small>Код вставки виджета</small>
            <CopyButton className="agent-widget-copy" label="Копировать" value={webWidgetSnippet(widget.widgetPublicKey)} />
          </div>
          <code>{webWidgetSnippet(widget.widgetPublicKey)}</code>
          <small>Вставьте перед &lt;/body&gt; на сайте</small>
        </div>
      )}
    </section>
  );
}

function ConnectionRow({ connection, subtitle, status, action, busy }: {
  connection: AgentConnection;
  subtitle?: string;
  status: { text: string; bg: string; color: string };
  action: { label: string; run: () => void } | null;
  busy: boolean;
}) {
  const tint = agentTint(connection.provider);
  return (
    <div className="agent-connection">
      <span className="agent-connection-tile" style={{ background: tint.bg, color: tint.color }}>
        <ChannelGlyph provider={connection.provider} size={16} />
      </span>
      <div>
        <strong>{connection.name}</strong>
        <small>{subtitle ?? connectionSubtitle(connection)}</small>
      </div>
      <b className="agent-chip" style={{ background: status.bg, color: status.color }}>{status.text}</b>
      {action && <button className="agent-connection-action" type="button" disabled={busy} onClick={action.run}>{action.label}</button>}
    </div>
  );
}

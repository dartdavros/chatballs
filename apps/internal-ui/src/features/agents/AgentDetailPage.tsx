import { Dropdown, Modal } from "antd";
import { useCallback, useEffect, useState } from "react";

import { LANGUAGES } from "@chatballs/shared";

import { api, ApiError } from "../../api/client";
import { ChannelGlyph } from "../../shared/badges";
import { SelectField } from "../../shared/form-controls";
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
import { t } from "../../i18n";

// Карточка агента (дизайн-базлайн v2, «Агенты Baseline», кадры G3–G5): слева —
// что агент знает и как говорит (инструкции, знания), справа — как он работает
// (назначение, подключения, модель). Изменения применяются сразу (ADR-CHATBALLS-0023).

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

  if (missing) return <EmptyState title={t("ai.agent_not_found")} />;
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
        text: caught instanceof ApiError ? caught.payload.detail ?? t("common.could_not_save") : t("common.could_not_save"),
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
          : t("ai.could_not_change_ai_status"),
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
            ? t("ai.agent_cannot_deleted_has_conversations")
            : t("ai.could_not_delete_agent"),
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
      setFeedback({ kind: "error", text: t("ai.could_not_detach_connection") });
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
            ? t("ai.connection_already_bound_another_agent")
            : t("ai.could_not_bind_connection"),
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
    { key: "copy-code", label: <button type="button" onClick={() => { setMenuOpen(false); void navigator.clipboard?.writeText(card.code); }}><Icon name="copy" size={15} />{t("ai.copy_snippet")}</button> },
    { type: "divider" as const },
    {
      key: "active",
      disabled: busy,
      label: (
        <button type="button" onClick={() => { setMenuOpen(false); void apply({ isActive: !card.isActive }); }}>
          <Icon name={card.isActive ? "xCircle" : "check"} size={15} />{card.isActive ? t("ai.turn_agent_off") : t("ai.turn_agent")}
        </button>
      ),
    },
    {
      key: "delete",
      disabled: busy,
      label: (
        <button className="danger" type="button" onClick={() => { setMenuOpen(false); setDeleting(true); }}>
          <Icon name="trash" size={15} />{t("ai.delete_agent")}</button>
      ),
    },
  ];

  return (
    <div className="agent-page">
      <BackLink label={t("common.agents")} onClick={openAgents} />

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
            <span><i style={{ background: card.groupId === null ? "var(--n-5)" : groupColorOf(card.groupId, card.groupColor) }} />{card.groupName ?? t("common.no_group")}</span>
            <i />
            <code>{card.code}</code>
            <i />
            {openDialogsLine(card.counters.openConversations)}
            <i />
            {t("ai.created_on", { date: createdLabel(card.createdAt) })}
          </p>
        </div>
        {canManage && (
          <div className="agent-head-actions">
            <Button variant="secondary" className="agent-toggle" icon={running ? "pause" : "bolt"} disabled={busy} onClick={() => void toggleAi()}>
              {running ? t("ai.stop_ai") : t("ai.start_ai")}
            </Button>
            <Dropdown menu={{ items: menuItems }} open={menuOpen} onOpenChange={setMenuOpen} trigger={["click"]} overlayClassName="app-dropdown">
              <button className="agent-head-menu" type="button" aria-label={t("ai.agent_actions")} title={t("common.actions")}><Icon name="more" size={17} strokeWidth={2} /></button>
            </Dropdown>
          </div>
        )}
      </header>

      {card.providerIntegrationId === null && (
        <div className="agent-blocker">
          <Icon name="alert" size={18} strokeWidth={2.2} />
          <div>
            <strong>{t("ai.ai_cannot_reply_no_provider")}</strong>
            <small>{t("ai.add_key_under_settings_ai")}</small>
          </div>
          {canManage && (
            <button type="button" onClick={openAiProvider}>{t("ai.open_settings")}<Icon name="external" size={13} strokeWidth={2.2} /></button>
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
          title={t("ai.delete_agent_2")}
          okText={t("common.delete")}
          cancelText={t("common.cancel")}
          okButtonProps={{ danger: true, disabled: busy }}
          onOk={() => void removeAgent()}
          onCancel={() => setDeleting(false)}
        >
          <p>{t("ai.agent_will_be_deleted", { name: card.name })}</p>
        </Modal>
      )}
    </div>
  );
}

// --- Инструкции (кадры G3/G5) ---

const INSTRUCTION_FIELDS = [
  { key: "persona", label: t("ai.who_what_does"), hint: t("ai.persona"), rows: 7, placeholder: "" },
  { key: "tone", label: t("ai.how_should_speak"), hint: t("ai.tone"), rows: 7, placeholder: t("ai.example_calmly_politely_formal_address") },
  { key: "instructions", label: t("ai.working_rules"), hint: t("ai.instructions"), rows: 10, placeholder: t("ai.example_do_not_quote_prices") },
] as const;

// Язык ответов клиенту (кадр G3). «Как у клиента» стоит первым и выбран по
// умолчанию: язык обращения — сигнал точнее любой настройки, он лежит прямо в
// сообщении. Явный язык нужен тем, кто отвечает ровно на одном независимо от
// того, на каком спросили. Подписи языков не переводятся — свой язык человек
// узнаёт по его собственному имени.
const ANSWER_LANGUAGES: ReadonlyArray<{ value: string; label: string; lang?: string }> = [
  { value: "MIRROR", label: t("ai.answer_language_mirror") },
  { value: "ORGANIZATION", label: t("ai.answer_language_organization") },
  ...LANGUAGES.map((item) => ({ value: item.code, label: item.label, lang: item.code })),
];

function answerLanguageLabel(value: string): string {
  return ANSWER_LANGUAGES.find((option) => option.value === value)?.label ?? value;
}

function InstructionsCard({ card, canManage, busy, apply }: {
  card: AgentCard;
  canManage: boolean;
  busy: boolean;
  apply: (patch: AgentPatch) => Promise<boolean>;
}) {
  const [draft, setDraft] = useState({ persona: card.persona, tone: card.tone, instructions: card.instructions, answerLanguage: card.answerLanguage });
  useEffect(() => {
    setDraft({ persona: card.persona, tone: card.tone, instructions: card.instructions, answerLanguage: card.answerLanguage });
  }, [card.persona, card.tone, card.instructions, card.answerLanguage]);
  const dirty =
    draft.persona !== card.persona ||
    draft.tone !== card.tone ||
    draft.instructions !== card.instructions ||
    draft.answerLanguage !== card.answerLanguage;

  return (
    <section className="agent-card">
      <div className="agent-card-head">
        <h3>{t("ai.instructions_2")}</h3>
        <small>{t("ai.system_prompt_assembled_from_three")}</small>
      </div>
      <div className="agent-field is-text agent-answer-language">
        <span>{t("ai.answer_language")}<small>{t("ai.answer_language_hint")}</small></span>
        {canManage ? (
          <div className="appearance-theme-options">
            {ANSWER_LANGUAGES.map((option) => (
              <button
                className={draft.answerLanguage === option.value ? "active" : ""}
                key={option.value}
                lang={option.lang}
                type="button"
                onClick={() => setDraft((current) => ({ ...current, answerLanguage: option.value }))}
              >
                {option.label}
              </button>
            ))}
          </div>
        ) : (
          <span className="agent-field-static">{answerLanguageLabel(card.answerLanguage)}</span>
        )}
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
          <small>{t("ai.there_unsaved_changes_they_take")}</small>
          <button type="button" disabled={busy} onClick={() => setDraft({ persona: card.persona, tone: card.tone, instructions: card.instructions, answerLanguage: card.answerLanguage })}>{t("ai.undo")}</button>
          <button className="is-primary" type="button" disabled={busy} onClick={() => void apply(draft)}>{t("common.save")}</button>
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
        <div><h3>{t("ai.knowledge")}</h3><small>{knowledgeLine(card)}</small></div>
        {canManage && (
          <button className="agent-inline-button" type="button" onClick={() => setPicking(true)}>
            <Icon name="plus" size={13} strokeWidth={2.2} />{t("ai.select")}</button>
        )}
      </div>
      {rows.length === 0 ? (
        <p className="agent-knowledge-empty">{t("ai.no_knowledge_attached_so_agent")}</p>
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
                <button className="agent-knowledge-remove" type="button" aria-label={t("common.remove")} title={t("common.remove")} onClick={() => void detach(row.kind, row.id)}>
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
      <h3>{t("ai.assignment")}</h3>
      <p>{t("ai.group_decides_which_operators_see")}</p>
      <div className="agent-side-fields">
        <label className="agent-field">
          <span>{t("common.title")}</span>
          {canManage
            ? <input value={name} onChange={(event) => setName(event.target.value)} onBlur={() => { if (dirty) void apply({ name: name.trim() }); }} />
            : <span className="agent-field-static">{card.name}</span>}
        </label>
        <SelectField
          adornment={<i className="agent-group-dot" style={{ background: card.groupId === null ? "var(--n-5)" : groupColorOf(card.groupId, card.groupColor) }} />}
          disabled={busy}
          label={t("common.group")}
          readOnly={!canManage}
          readOnlyText={card.groupName ?? t("common.no_group")}
          value={card.groupId === null ? "" : String(card.groupId)}
          onChange={(next) => void apply({ groupId: next ? Number(next) : null })}
          options={[["", t("common.no_group")], ...groups.map((group) => [String(group.id), group.name] as [string, string])]}
        />
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
      <h3>{t("common.model")}</h3>
      <p>{t("ai.provider_key_lives_under_settings")}</p>
      <div className="agent-side-fields">
        <SelectField
          disabled={busy}
          invalid={missingProvider}
          label={t("ai.provider")}
          readOnly={!canManage}
          readOnlyText={providerName || t("ai.not_selected")}
          value={card.providerIntegrationId ? String(card.providerIntegrationId) : ""}
          onChange={(next) => void apply({ providerIntegrationId: next ? Number(next) : null })}
          options={[["", t("ai.not_selected")], ...providers.map((item) => [String(item.id), item.name] as [string, string])]}
        />
        <label className="agent-field is-model">
          <span>{t("common.model")}</span>
          <span className="agent-field-control">
            <span className={`agent-field-static ${missingProvider ? "is-placeholder" : ""}`}>{missingProvider ? t("ai.pick_provider") : card.model}</span>
            <Icon name="search" size={14} strokeWidth={1.8} />
          </span>
        </label>
        <div className="agent-limit">
          <span>{t("ai.daily_limit")}</span>
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
        <h3>{t("common.connections")}</h3>
        {canManage && (
          <button className="link has-icon" type="button" onClick={openIntegrations}>{t("common.integrations")}<Icon name="external" size={13} strokeWidth={2.2} /></button>
        )}
      </div>
      <p>{t("ai.customers_reach_agent_through_these")}</p>
      {card.connections.map((connection) => (
        <ConnectionRow
          connection={connection}
          status={connectionStatusMeta(connection.status)}
          action={canManage ? { label: t("ai.unbind"), run: () => unbind(connection.id) } : null}
          busy={busy}
          key={connection.id}
        />
      ))}
      {canManage && available.map((integration) => (
        <ConnectionRow
          connection={{ id: integration.id, provider: integration.provider, name: integration.name, status: integration.status, botUsername: "", email: "", allowedOrigins: [], widgetPublicKey: "" }}
          subtitle={t("ai.free_connection")}
          status={{ text: t("ai.free"), bg: "var(--n-9)", color: "var(--n-4)" }}
          action={{ label: t("ai.bind"), run: () => bind(integration.id) }}
          busy={busy}
          key={`free-${integration.id}`}
        />
      ))}
      {widget && (
        <div className="agent-widget">
          <div>
            <small>{t("ai.widget_embed_snippet")}</small>
            <CopyButton className="agent-widget-copy" label={t("common.copy")} value={webWidgetSnippet(widget.widgetPublicKey)} />
          </div>
          <code>{webWidgetSnippet(widget.widgetPublicKey)}</code>
          <small>{t("ai.paste_before_lt_body_gt")}</small>
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

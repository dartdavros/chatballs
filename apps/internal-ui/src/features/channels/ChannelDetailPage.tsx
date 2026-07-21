import { useEffect, useState } from "react";

import { ApiError } from "../../api/client";
import { Icon } from "../../shared/icons";
import { EmptyState, LoadingState } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
import { formatDate, productAccent } from "../../shared/utils";
import type { Department, Product, RouteKey } from "../../types";
import { ChannelBadge, providerLabel } from "./ChannelBadge";
import { ChannelPolicySection } from "./ChannelPolicySection";
import { deleteChannel, loadChannel, unbindConnection, updateChannel } from "./api";
import { BLOCKER_LABELS } from "./model";
import type { Channel, DeletionBlocker, PolicyFlag, PolicyViolation } from "./types";
import "./styles.css";

type Feedback = { kind: "error" | "warning"; text: string } | null;

export function ChannelDetailPage({
  channelId,
  departments,
  products,
  canManage,
  setRoute,
  openAgent,
  openChannels,
}: {
  channelId: number | null;
  departments: Department[];
  products: Product[];
  canManage: boolean;
  setRoute: (route: RouteKey) => void;
  openAgent: (agentId: number) => void;
  openChannels: () => void;
}) {
  const [channel, setChannel] = useState<Channel | null>(null);
  const [missing, setMissing] = useState(false);
  const [feedback, setFeedback] = useState<Feedback>(null);
  const [blockers, setBlockers] = useState<DeletionBlocker[] | null>(null);

  async function reload() {
    if (channelId === null) return;
    try {
      const response = await loadChannel(channelId);
      setChannel(response.channel);
      setMissing(false);
    } catch (error) {
      // Канал вне scope не раскрывает своё существование.
      if (error instanceof ApiError && error.status === 404) setMissing(true);
    }
  }

  useEffect(() => {
    void reload();
  }, [channelId]);

  async function patch(body: Parameters<typeof updateChannel>[1]) {
    if (!channel) return;
    setFeedback(null);
    try {
      const response = await updateChannel(channel.id, body);
      setChannel(response.channel);
      const warning = response.warnings?.find((item) => item.code === "agent_still_active");
      if (warning) {
        setFeedback({
          kind: "warning",
          text: "Канал деактивирован, но агент остаётся активным и продолжает занимать слот. Остановите его на странице агента.",
        });
      }
    } catch (error) {
      if (error instanceof ApiError) {
        const violations = (error.payload as { violations?: PolicyViolation[] }).violations;
        setFeedback({
          kind: "error",
          text: violations?.length
            ? violations.map((item) => `${item.detail} (${item.rule})`).join("; ")
            : error.message,
        });
      }
    }
  }

  async function remove() {
    if (!channel) return;
    try {
      await deleteChannel(channel.id);
      openChannels();
    } catch (error) {
      if (error instanceof ApiError) {
        const payload = error.payload as { blockers?: DeletionBlocker[] };
        if (payload.blockers) setBlockers(payload.blockers);
        else setFeedback({ kind: "error", text: error.message });
      }
    }
  }

  if (missing) return <EmptyState title="Канал не найден" />;
  if (!channel) return <LoadingState />;

  const accent = channel.product ? productAccent(channel.product.code) : null;

  return (
    <div className="channel-detail">
      <div className="channel-breadcrumb">
        <a
          href="#"
          onClick={(event) => {
            event.preventDefault();
            openChannels();
          }}
        >
          Каналы
        </a>
        <span>/</span>
        <strong>{channel.name}</strong>
      </div>

      <div className="channel-detail-header">
        <div>
          <h1>{channel.name}</h1>
          <div className="channel-detail-meta">
            <code>{channel.code}</code>
            <span>·</span>
            {channel.departmentName ?? <span className="channel-chip">Без отдела</span>}
            <span>·</span>
            {channel.product && accent ? (
              <span className="channel-detail-product">
                <i style={{ background: accent.color }} />
                {channel.product.name}
              </span>
            ) : (
              <span className="channel-muted">— непродуктовый</span>
            )}
          </div>
        </div>
        <div className="channel-detail-actions">
          <span
            className={`channel-state-pill ${channel.isActive ? "is-active" : "is-archived"}`}
          >
            <i />
            {channel.isActive ? "Активен" : "Архивный"}
          </span>
          {canManage && (
            <Button
              variant="secondary"
              icon="pause"
              onClick={() => patch({ isActive: !channel.isActive })}
            >
              {channel.isActive ? "Деактивировать" : "Активировать"}
            </Button>
          )}
          {canManage && (
            <Button variant="danger-outline" icon="trash" onClick={remove}>
              Удалить
            </Button>
          )}
        </div>
      </div>

      {feedback && <div className={`channel-feedback is-${feedback.kind}`}>{feedback.text}</div>}

      {blockers && (
        <div className="channel-blockers">
          <div className="channel-blockers-head">
            <strong>Канал нельзя удалить</strong>
            <p>Есть связанные записи. Вместо удаления используйте деактивацию — история сохранится.</p>
          </div>
          <div className="channel-blockers-list">
            {blockers.map((item) => (
              <div key={item.type}>
                <span>{BLOCKER_LABELS[item.type] ?? item.type}</span>
                <b>{item.count}</b>
              </div>
            ))}
          </div>
          <div className="channel-blockers-actions">
            <Button variant="secondary" onClick={() => setBlockers(null)}>
              Закрыть
            </Button>
            {channel.isActive && (
              <Button
                variant="secondary"
                onClick={async () => {
                  setBlockers(null);
                  await patch({ isActive: false });
                }}
              >
                Деактивировать вместо удаления
              </Button>
            )}
          </div>
        </div>
      )}

      <section className="channel-card-section">
        <header>
          <h3>Назначение</h3>
          <span>Отдел и продукт редактируются здесь</span>
        </header>
        <div className="channel-assignment">
          <label>
            <span>Отдел</span>
            <select
              value={channel.departmentId ?? ""}
              disabled={!canManage}
              onChange={(event) =>
                patch({ departmentId: event.target.value ? Number(event.target.value) : null })
              }
            >
              <option value="">Без отдела</option>
              {departments.map((department) => (
                <option value={department.id} key={department.id}>
                  {department.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Продукт</span>
            <select
              value={channel.product?.id ?? ""}
              disabled={!canManage}
              onChange={(event) =>
                patch({ productId: event.target.value ? Number(event.target.value) : null })
              }
            >
              <option value="">— непродуктовый</option>
              {products.map((product) => (
                <option value={product.id} key={product.id}>
                  {product.name}
                </option>
              ))}
            </select>
          </label>
          <div className="channel-readonly">
            <span>Код</span>
            <code>{channel.code}</code>
          </div>
          <div className="channel-readonly">
            <span>Создан</span>
            <b>{formatDate(channel.createdAt)}</b>
          </div>
        </div>
      </section>

      <ChannelPolicySection
        channel={channel}
        canManage={canManage}
        onToggle={(flag: PolicyFlag, value) => patch({ policy: { [flag]: value } })}
      />

      <section className="channel-card-section">
        <header>
          <h3>Подключения</h3>
        </header>
        {channel.connections.length === 0 ? (
          <p className="channel-muted">Подключений нет. Привяжите их в разделе «Интеграции».</p>
        ) : (
          <div className="channel-connections">
            {channel.connections.map((connection) => (
              <div className="channel-connection" key={connection.id}>
                <ChannelBadge provider={connection.provider} />
                <div className="channel-connection-text">
                  <strong>{connection.name}</strong>
                  <span>{providerLabel(connection.provider)}</span>
                </div>
                <span className={`channel-status channel-status--${connection.status.toLowerCase()}`}>
                  <i />
                  {connection.status}
                </span>
                {canManage && (
                  <Button
                    variant="secondary"
                    onClick={async () => {
                      await unbindConnection(channel.id, connection.id);
                      await reload();
                    }}
                  >
                    Отвязать
                  </Button>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Одна строка сводки и переход наружу: редактор агента остаётся на его странице. */}
      <section className="channel-card-section channel-agent-section">
        <div className="channel-section-eyebrow">AI-АГЕНТ</div>
        {channel.agent ? (
          <div className="channel-agent-row">
            <span className="channel-agent-mark">
              <Icon name="robot" size={18} />
            </span>
            <div className="channel-agent-summary">
              <b>{channel.agent.name}</b>
              <span>·</span>
              <span
                className={`channel-status ${
                  channel.agent.status === "ACTIVE" ? "channel-status--active" : "channel-status--draft"
                }`}
              >
                <i />
                {channel.agent.status === "ACTIVE" ? "Активен" : "Черновик"}
              </span>
              <span>·</span>
              <code>{channel.agent.model}</code>
            </div>
            <a
              href="#"
              className="channel-agent-link"
              onClick={(event) => {
                event.preventDefault();
                openAgent(channel.agent!.id);
              }}
            >
              Открыть агента
              <Icon name="arrow" size={14} />
            </a>
          </div>
        ) : (
          <div className="channel-agent-none">
            <span className="channel-agent-mark">
              <Icon name="robot" size={22} />
            </span>
            <strong>Агента нет, канал ведут операторы</strong>
            <p>Валидное состояние канала. Агент создаётся отдельным действием в разделе AI.</p>
            <a
              href="#"
              onClick={(event) => {
                event.preventDefault();
                setRoute("aiAgentCreate");
              }}
            >
              Создать агента в разделе AI
              <Icon name="arrow" size={14} />
            </a>
          </div>
        )}
      </section>

      <section className="channel-card-section">
        <header>
          <h3>Счётчики</h3>
        </header>
        <div className="channel-counters">
          <div>
            <span>ОТКРЫТЫЕ ДИАЛОГИ</span>
            <b>{channel.counters.openConversations}</b>
          </div>
          <div>
            <span>ПОДКЛЮЧЕНИЯ</span>
            <b>{channel.counters.connections}</b>
          </div>
        </div>
      </section>
    </div>
  );
}

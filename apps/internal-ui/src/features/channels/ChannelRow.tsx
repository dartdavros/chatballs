import { Dropdown } from "antd";

import { ChannelBadge } from "../../shared/badges";
import { Icon } from "../../shared/icons";
import { ProductTag, StatusPill } from "../../shared/ui";
import { agentStatus, deletionHint } from "./model";
import type { Channel } from "./types";

function AgentCell({ channel, canOpenAgent, openAgent }: { channel: Channel; canOpenAgent: boolean; openAgent: (agentId: number) => void }) {
  if (!channel.isActive) {
    return <StatusPill status="archived" />;
  }
  if (!channel.agent) {
    // Канал без агента — валидное операторское состояние, а не ошибка.
    return (
      <div className="channel-agent-empty">
        <span>Нет агента</span>
        <em>операторский канал</em>
      </div>
    );
  }
  return (
    <div className="channel-agent-cell">
      {canOpenAgent ? (
        <button className="link" type="button" onClick={(event) => { event.stopPropagation(); openAgent(channel.agent!.id); }}>
          {channel.agent.name}
        </button>
      ) : <strong>{channel.agent.name}</strong>}
      <StatusPill status={agentStatus(channel.agent.status)} />
    </div>
  );
}

export function ChannelRow({
  channel,
  canManageLifecycle,
  canOpenAgent,
  menuId,
  setMenuId,
  openChannel,
  openAgent,
  requestToggleActive,
  onDelete,
}: {
  channel: Channel;
  canManageLifecycle: boolean;
  canOpenAgent: boolean;
  menuId: number | null;
  setMenuId: (channelId: number | null) => void;
  openChannel: (channelId: number) => void;
  openAgent: (agentId: number) => void;
  requestToggleActive: (channel: Channel) => void;
  onDelete: (channel: Channel) => void;
}) {
  const blocked = deletionHint(channel);
  const openItem = {
    key: "open",
    label: (
      <button type="button" onClick={() => openChannel(channel.id)}>
        <Icon name="external" size={15} />
        Открыть
      </button>
    ),
  };
  const menuItems = channel.isActive ? [
    openItem,
    ...(canManageLifecycle
      ? [
          { type: "divider" as const },
          {
            key: "status",
            label: (
              <button className="warning" type="button" onClick={() => requestToggleActive(channel)}>
                <Icon name="pause" size={15} />
                Деактивировать
              </button>
            ),
          },
          {
            key: "delete",
            disabled: blocked !== null,
            label: (
              <button className="danger" type="button" onClick={() => onDelete(channel)}>
                <Icon name="trash" size={15} />
                <span>Удалить{blocked && <small>{blocked}</small>}</span>
              </button>
            ),
          },
        ]
      : []),
  ] : [
    ...(canManageLifecycle
      ? [{
          key: "status",
          label: (
            <button type="button" onClick={() => requestToggleActive(channel)}>
              <Icon name="refresh" size={15} />
              Активировать
            </button>
          ),
        }]
      : [openItem]),
  ];

  return (
    <tr className={channel.isActive ? "" : "is-archived"} onClick={() => openChannel(channel.id)}>
      <td>
        <button
          className="link is-neutral is-strong"
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            openChannel(channel.id);
          }}
        >
          {channel.name}
        </button>
        <div className="channel-sub">
          <code>{channel.code}</code>
          {" · "}
          {channel.departmentName ?? <span className="channel-badge channel-badge--plain">Без отдела</span>}
        </div>
      </td>
      <td>
        {channel.product ? <ProductTag product={channel.product} /> : <span className="channel-muted">— непродуктовый</span>}
      </td>
      <td>
        {channel.connections.length ? (
          <span className="channel-badges">
            {channel.connections.map((connection) => (
              <ChannelBadge key={connection.id} provider={connection.provider} />
            ))}
          </span>
        ) : (
          <span className="channel-muted">—</span>
        )}
      </td>
      <td>
        <AgentCell channel={channel} canOpenAgent={canOpenAgent} openAgent={openAgent} />
      </td>
      <td className="numeric">{channel.counters.openConversations}</td>
      <td className="row-actions" onClick={(event) => event.stopPropagation()}>
        <Dropdown
          menu={{ items: menuItems }}
          open={menuId === channel.id}
          onOpenChange={(open) => setMenuId(open ? channel.id : null)}
          trigger={["click"]}
          overlayClassName="app-dropdown is-channels-menu"
        >
          <button className="row-menu-button" type="button" aria-label={`Действия: ${channel.name}`}>
            <Icon name="more" />
          </button>
        </Dropdown>
      </td>
    </tr>
  );
}

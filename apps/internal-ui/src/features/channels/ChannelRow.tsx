import { Dropdown } from "antd";

import { Icon } from "../../shared/icons";
import { StatusPill } from "../../shared/ui";
import { ChannelBadge } from "./ChannelBadge";
import { ChannelProductMark } from "./ChannelProductMark";
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
  canManageConnections,
  canOpenAgent,
  menuId,
  setMenuId,
  openChannel,
  openConnections,
  openAgent,
  requestToggleActive,
  onDelete,
}: {
  channel: Channel;
  canManageLifecycle: boolean;
  canManageConnections: boolean;
  canOpenAgent: boolean;
  menuId: number | null;
  setMenuId: (channelId: number | null) => void;
  openChannel: (channelId: number) => void;
  openConnections: (channelId: number) => void;
  openAgent: (agentId: number) => void;
  requestToggleActive: (channel: Channel) => void;
  onDelete: (channel: Channel) => void;
}) {
  const blocked = deletionHint(channel);
  const menuItems = [
    {
      key: "open",
      label: (
        <button type="button" onClick={() => openChannel(channel.id)}>
          <Icon name="external" size={15} />
          Открыть
        </button>
      ),
    },
    // Пункты, недоступные по capability, не показываются вовсе.
    ...(canManageConnections && channel.isActive
      ? [{
          key: "bind",
          label: (
            <button type="button" onClick={() => openConnections(channel.id)}>
              <Icon name="plug" size={15} />
              Привязать подключение
            </button>
          ),
        }]
      : []),
    ...(canManageLifecycle
      ? [
          { type: "divider" as const },
          {
            key: "status",
            label: (
              <button className="warning" type="button" onClick={() => requestToggleActive(channel)}>
                <Icon name="pause" size={15} />
                {channel.isActive ? "Деактивировать" : "Активировать"}
              </button>
            ),
          },
          ...(channel.isActive ? [{
            key: "delete",
            disabled: blocked !== null,
            label: (
              <button className="danger" type="button" onClick={() => onDelete(channel)}>
                <Icon name="trash" size={15} />
                <span>Удалить{blocked && <small>{blocked}</small>}</span>
              </button>
            ),
          }] : []),
        ]
      : []),
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
        <ChannelProductMark product={channel.product} />
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
          overlayClassName="app-dropdown"
        >
          <button className="row-menu-button" type="button" aria-label={`Действия: ${channel.name}`}>
            <Icon name="more" />
          </button>
        </Dropdown>
      </td>
    </tr>
  );
}

import { useEffect, useMemo, useState } from "react";

import { ApiError } from "../../api/client";
import { PageHeader } from "../../shared/ui";
import { Button, SearchInput, UnderlineTabs } from "../../shared/ui-controls";
import { Icon } from "../../shared/icons";
import { EmptyState, LoadingState } from "../../shared/ui";
import { listChannels, updateChannel } from "./api";
import { ChannelsTable } from "./ChannelsTable";
import { departmentTabs, filterChannels } from "./model";
import type { Channel } from "./types";
import "./styles.css";

export function ChannelsPage({
  canManage,
  openChannel,
  openChannelCreate,
  openAgent,
}: {
  canManage: boolean;
  openChannel: (channelId: number) => void;
  openChannelCreate: () => void;
  openAgent: (agentId: number) => void;
}) {
  const [channels, setChannels] = useState<Channel[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState("all");
  const [search, setSearch] = useState("");
  const [showArchived, setShowArchived] = useState(false);

  async function reload() {
    try {
      const response = await listChannels();
      setChannels(response.items);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof ApiError ? loadError.message : "Не удалось загрузить каналы");
    }
  }

  useEffect(() => {
    void reload();
  }, []);

  const tabs = useMemo(() => departmentTabs(channels ?? []), [channels]);
  const visible = useMemo(
    () => filterChannels(channels ?? [], { tab, search, showArchived }),
    [channels, tab, search, showArchived],
  );

  async function toggleActive(channel: Channel) {
    await updateChannel(channel.id, { isActive: !channel.isActive });
    await reload();
  }

  if (error) return <EmptyState title={error} />;
  if (!channels) return <LoadingState />;

  const archived = channels.filter((channel) => !channel.isActive).length;

  return (
    <>
      <PageHeader
        title="Каналы"
        text="Точка маршрутизации диалогов: связывает отдел, продукт, подключения и — необязательно — AI-агента"
        action={
          canManage ? (
            <Button variant="primary" icon="plus" onClick={openChannelCreate}>
              Создать канал
            </Button>
          ) : undefined
        }
      />
      {channels.length === 0 ? (
        <div className="channels-empty">
          <span className="channels-empty-mark">
            <Icon name="gitBranch" size={24} />
          </span>
          <strong>Создайте первый канал</strong>
          <p>
            Канал маршрутизирует диалоги от подключений к отделу, продукту и — при необходимости —
            к AI-агенту.
          </p>
          {canManage && (
            <Button variant="primary" onClick={openChannelCreate}>
              Создать канал
            </Button>
          )}
        </div>
      ) : (
        <>
          <div className="channels-toolbar">
            <UnderlineTabs items={tabs} value={tab} onChange={setTab} />
            <div className="channels-toolbar-tools">
              <SearchInput placeholder="Поиск по имени и коду" value={search} onChange={setSearch} />
              <label className="channels-archive-toggle">
                <input
                  type="checkbox"
                  checked={showArchived}
                  onChange={(event) => setShowArchived(event.target.checked)}
                />
                <span />
                Показывать архивные
              </label>
            </div>
          </div>
          <ChannelsTable
            channels={visible}
            canManage={canManage}
            openChannel={openChannel}
            openAgent={openAgent}
            toggleActive={toggleActive}
            footer={`${channels.length} каналов${archived ? ` · ${archived} архивных` : ""}`}
          />
        </>
      )}
    </>
  );
}

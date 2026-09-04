import { hasCapability } from "../../auth/access";
import { SwitchButton } from "../../shared/form-controls";
import { Icon } from "../../shared/icons";
import { ContentState, ErrorScreen, LoadingState, PageHeader } from "../../shared/ui";
import { Button, SearchInput, UnderlineTabs } from "../../shared/ui-controls";
import type { EmployeeGroup, SessionUser } from "../../types";
import { ChannelDeactivationDialog } from "./ChannelDeactivationDialog";
import { ChannelDeleteDialog } from "./ChannelDeleteDialog";
import { ChannelsTable } from "./ChannelsTable";
import { archivedCountLabel, channelCountLabel } from "./model";
import type { Channel } from "./types";
import { useChannelsPage } from "./useChannelsPage";

export function ChannelsPage({
  user, groups, openChannel, openChannelCreate, openAgent,
}: {
  user: SessionUser;
  groups: EmployeeGroup[];
  openChannel: (channelId: number) => void;
  openChannelCreate: () => void;
  openAgent: (agentId: number) => void;
}) {
  const page = useChannelsPage(groups);
  const canManageLifecycle = hasCapability(user, "channels.manage");
  const canOpenAgent = (_channel: Channel) => hasCapability(user, "ai.view");
  const openChannelCard = (channelId: number) => {
    if (window.location.hash) {
      window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}`);
    }
    openChannel(channelId);
  };

  if (page.failed) return <ErrorScreen retry={() => void page.reload()} />;
  if (!page.channels) return <LoadingState />;

  return (
    <>
      <PageHeader
        title="Каналы"
        text="Точка маршрутизации диалогов: связывает группу, продукт, подключения и — необязательно — AI-агента. Группа определяет, какие сотрудники видят диалоги канала; без группы диалоги видны всем"
        action={canManageLifecycle ? <Button className="channel-create-action" variant="primary" icon="plus" onClick={openChannelCreate}>Создать канал</Button> : undefined}
      />

      {page.feedback && <div className="channel-feedback is-error">{page.feedback}</div>}

      {page.channels.length === 0 ? (
        <ContentState
          icon={<Icon name="route" size={24} />}
          title="Создайте первый канал"
          text="Канал маршрутизирует диалоги от подключений к группе, продукту и — при необходимости — к AI-агенту. Группа определяет, какие сотрудники видят диалоги канала; без группы диалоги видны всем."
          action={canManageLifecycle ? <Button className="channel-state-action" variant="primary" onClick={openChannelCreate}>Создать канал</Button> : undefined}
        />
      ) : (
        <>
          <div className="channels-toolbar">
            <UnderlineTabs className="channels-tabs" items={page.tabs} value={page.tab} onChange={page.setTab} />
            <div className="channels-toolbar-tools">
              <SearchInput className="channels-search" placeholder="Поиск по имени и коду" value={page.search} onChange={page.setSearch} />
              <div className="channels-archive-toggle">
                <SwitchButton className="ui-switch" checked={page.showArchived} label="Показывать архивные" onClick={() => page.setShowArchived(!page.showArchived)} />
                <span>Показывать архивные</span>
              </div>
            </div>
          </div>
          <ChannelsTable
            channels={page.visible}
            canManageLifecycle={canManageLifecycle}
            canOpenAgent={canOpenAgent}
            openChannel={openChannelCard}
            openAgent={openAgent}
            requestToggleActive={page.requestToggleActive}
            onDelete={page.setDeleteTarget}
            footer={`${channelCountLabel(page.channels.length)}${page.archived ? ` · ${archivedCountLabel(page.archived)}` : ""}`}
          />
        </>
      )}

      {page.deleteTarget && (
        <ChannelDeleteDialog
          channel={page.deleteTarget}
          open
          blockers={page.blockers}
          busy={page.busy}
          onConfirm={() => void page.removeChannel(page.deleteTarget!)}
          onDeactivate={() => {
            const target = page.deleteTarget!;
            page.closeDelete();
            page.requestToggleActive(target);
          }}
          onClose={page.closeDelete}
        />
      )}

      {page.deactivationTarget?.agent && (
        <ChannelDeactivationDialog
          channel={page.deactivationTarget}
          open
          busy={page.busy}
          onConfirm={async () => {
            const target = page.deactivationTarget!;
            page.setDeactivationTarget(null);
            await page.toggleActive(target);
          }}
          onOpenAgent={() => openAgent(page.deactivationTarget!.agent!.id)}
          onClose={() => page.setDeactivationTarget(null)}
        />
      )}
    </>
  );
}

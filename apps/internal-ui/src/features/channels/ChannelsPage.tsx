import { hasCapability, scopeDepartments } from "../../auth/access";
import { SwitchButton } from "../../shared/form-controls";
import { Icon } from "../../shared/icons";
import { ErrorScreen, LoadingState, PageHeader } from "../../shared/ui";
import { Button, SearchInput, UnderlineTabs } from "../../shared/ui-controls";
import type { Department, SessionUser } from "../../types";
import { ChannelDeactivationDialog } from "./ChannelDeactivationDialog";
import { ChannelDeleteDialog } from "./ChannelDeleteDialog";
import { ChannelsTable } from "./ChannelsTable";
import type { Channel } from "./types";
import { useChannelsPage } from "./useChannelsPage";

export function ChannelsPage({
  user, departments, openChannel, openChannelCreate, openAgent,
}: {
  user: SessionUser;
  departments: Department[];
  openChannel: (channelId: number) => void;
  openChannelCreate: () => void;
  openAgent: (agentId: number) => void;
}) {
  const page = useChannelsPage();
  const scopedCodes = scopeDepartments(user, "channels.view");
  const scopedNames = scopedCodes
    ?.map((code) => departments.find((department) => department.code === code)?.name ?? code)
    .join(", ");
  const canManageLifecycle = hasCapability(user, "channels.manage");
  const canManageConnections = hasCapability(user, "integrations.manage");
  const canOpenAgent = (channel: Channel) => hasCapability(user, "ai.view", channel.department ?? undefined);
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
        text="Точка маршрутизации диалогов: связывает отдел, продукт, подключения и — необязательно — AI-агента"
        action={canManageLifecycle ? <Button variant="primary" icon="plus" onClick={openChannelCreate}>Создать канал</Button> : undefined}
      />

      {page.feedback && <div className="channel-feedback is-error">{page.feedback}</div>}

      {scopedNames && (
        <div className="channel-notice">
          <div>
            <strong>Доступ ограничен отделом</strong>
            <p>Показаны каналы отдела «{scopedNames}». Каналы других отделов и канал без отдела не отображаются; счётчики фильтров считаются по видимым каналам.</p>
          </div>
        </div>
      )}

      {page.channels.length === 0 ? (
        <div className="channels-empty">
          <span className="channels-empty-mark"><Icon name="route" size={24} /></span>
          <strong>Создайте первый канал</strong>
          <p>Канал маршрутизирует диалоги от подключений к отделу, продукту и — при необходимости — к AI-агенту.</p>
          {canManageLifecycle && <Button variant="primary" onClick={openChannelCreate}>Создать канал</Button>}
        </div>
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
            canManageConnections={canManageConnections}
            canOpenAgent={canOpenAgent}
            openChannel={openChannelCard}
            openConnections={(channelId) => {
              window.location.hash = "connections";
              openChannel(channelId);
            }}
            openAgent={openAgent}
            requestToggleActive={page.requestToggleActive}
            onDelete={page.setDeleteTarget}
            footer={`${page.channels.length} каналов${page.archived ? ` · ${page.archived} архивных` : ""}`}
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

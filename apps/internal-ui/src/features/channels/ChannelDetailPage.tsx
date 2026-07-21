import { hasCapability, scopeDepartments } from "../../auth/access";
import { EmptyState, ErrorScreen, LoadingState } from "../../shared/ui";
import type { Department, Product, RouteKey, SessionUser } from "../../types";
import { ChannelAgentSection } from "./ChannelAgentSection";
import { ChannelArchivedNotice } from "./ChannelArchivedNotice";
import { ChannelAssignmentSection } from "./ChannelAssignmentSection";
import { ChannelConnectionsSection } from "./ChannelConnectionsSection";
import { ChannelCountersSection } from "./ChannelCountersSection";
import { ChannelDeactivationDialog } from "./ChannelDeactivationDialog";
import { ChannelDeleteDialog } from "./ChannelDeleteDialog";
import { ChannelDetailHeader } from "./ChannelDetailHeader";
import { ChannelPolicySection } from "./ChannelPolicySection";
import type { PolicyFlag } from "./types";
import { useChannelDetail } from "./useChannelDetail";

export function ChannelDetailPage({
  channelId, departments, products, user, setRoute, openAgent, openChannels,
}: {
  channelId: number | null;
  departments: Department[];
  products: Product[];
  user: SessionUser;
  setRoute: (route: RouteKey) => void;
  openAgent: (agentId: number) => void;
  openChannels: () => void;
}) {
  const detail = useChannelDetail(channelId, openChannels);

  if (detail.missing) return <EmptyState title="Канал не найден" />;
  if (detail.loadFailed) return <ErrorScreen retry={() => void detail.reload()} />;
  if (!detail.channel) return <LoadingState />;

  const { channel } = detail;
  const organizationManage = hasCapability(user, "channels.manage");
  const canManageCurrent = organizationManage || Boolean(
    channel.department && hasCapability(user, "channels.manage", channel.department),
  );
  const managedDepartments = scopeDepartments(user, "channels.manage");
  const editableDepartments = organizationManage || managedDepartments === null
    ? departments
    : departments.filter((department) => managedDepartments.includes(department.code));
  const canOpenAgent = hasCapability(user, "ai.view", channel.department ?? undefined);
  const canOpenDialogs = hasCapability(user, "conversations.view", channel.department ?? undefined);

  return (
    <div className="channel-detail">
      <ChannelDetailHeader
        channel={channel}
        canEdit={canManageCurrent}
        canManageLifecycle={organizationManage}
        editing={detail.editing}
        busy={detail.busy}
        onEdit={() => detail.setEditing(true)}
        onToggleActive={detail.requestToggleActive}
        onDelete={() => detail.setDeleting(true)}
        openChannels={openChannels}
      />

      {detail.feedback && <div className={`channel-feedback is-${detail.feedback.kind}`}>{detail.feedback.text}</div>}
      {!channel.isActive && <ChannelArchivedNotice canManage={organizationManage} busy={detail.busy} onActivate={() => void detail.patch({ isActive: true })} />}

      <ChannelAssignmentSection
        key={`${channel.name}-${channel.departmentId}-${channel.product?.id ?? "none"}-${String(detail.editing)}`}
        channel={channel}
        departments={editableDepartments}
        products={products}
        editing={detail.editing}
        canEditName={canManageCurrent}
        canEditDepartment={canManageCurrent}
        canEditProduct={organizationManage}
        allowNoDepartment={organizationManage}
        busy={detail.busy}
        onSave={(assignment) => void detail.patch(assignment)}
        onCancel={() => detail.setEditing(false)}
      />

      <ChannelPolicySection
        channel={channel}
        canManage={organizationManage}
        busy={detail.busy}
        onToggle={(flag: PolicyFlag, value) => void detail.patch({ policy: { [flag]: value } })}
        onAssignProduct={() => detail.setEditing(true)}
      />

      <ChannelConnectionsSection
        channel={channel}
        canManage={hasCapability(user, "integrations.manage")}
        initiallyOpen={window.location.hash === "#connections"}
        onChanged={detail.setChannel}
      />
      <ChannelAgentSection channel={channel} canOpenAgent={canOpenAgent} openAgent={openAgent} openAgentCreate={() => setRoute("aiAgentCreate")} />
      <ChannelCountersSection channel={channel} canOpenDialogs={canOpenDialogs} openDialogs={() => setRoute("salesDialogs")} />

      <ChannelDeleteDialog
        channel={channel}
        open={detail.deleting}
        blockers={detail.blockers}
        busy={detail.busy}
        onConfirm={() => void detail.remove()}
        onDeactivate={() => {
          detail.closeDeleteDialog();
          detail.requestToggleActive();
        }}
        onClose={detail.closeDeleteDialog}
      />

      {channel.agent && (
        <ChannelDeactivationDialog
          channel={channel}
          open={detail.confirmingDeactivation}
          busy={detail.busy}
          onConfirm={async () => {
            detail.setConfirmingDeactivation(false);
            await detail.patch({ isActive: false });
          }}
          onOpenAgent={() => openAgent(channel.agent!.id)}
          onClose={() => detail.setConfirmingDeactivation(false)}
        />
      )}
    </div>
  );
}

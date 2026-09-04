import { useEffect } from "react";

import { hasCapability } from "../../auth/access";
import { EmptyState, ErrorScreen, LoadingState } from "../../shared/ui";
import type { EmployeeGroup, Product, RouteKey, SessionUser } from "../../types";
import { ChannelAgentSection } from "./ChannelAgentSection";
import { ChannelArchivedNotice } from "./ChannelArchivedNotice";
import { ChannelAssignmentSection } from "./ChannelAssignmentSection";
import { ChannelConnectionsSection } from "./ChannelConnectionsSection";
import { ChannelCountersSection } from "./ChannelCountersSection";
import { ChannelDangerActions } from "./ChannelDangerActions";
import { ChannelDeactivationDialog } from "./ChannelDeactivationDialog";
import { ChannelDeleteDialog } from "./ChannelDeleteDialog";
import { ChannelDetailHeader } from "./ChannelDetailHeader";
import { ChannelPolicySection } from "./ChannelPolicySection";
import { channelDraftRequest } from "./channel-editor";
import type { PolicyFlag } from "./types";
import { useChannelEditor } from "./useChannelEditor";
import { useChannelDetail } from "./useChannelDetail";

export function ChannelDetailPage({
  channelId, groups, products, user, setRoute, openAgent, openChannels, onChannelLoaded,
}: {
  channelId: number | null;
  groups: EmployeeGroup[];
  products: Product[];
  user: SessionUser;
  setRoute: (route: RouteKey) => void;
  openAgent: (agentId: number) => void;
  openChannels: () => void;
  onChannelLoaded: (name: string | null) => void;
}) {
  const detail = useChannelDetail(channelId, openChannels);
  const editor = useChannelEditor(detail.channel);

  useEffect(() => {
    onChannelLoaded(detail.channel?.name ?? null);
    return () => onChannelLoaded(null);
  }, [detail.channel?.name, onChannelLoaded]);

  if (detail.missing) return <EmptyState title="Канал не найден" />;
  if (detail.loadFailed) return <ErrorScreen retry={() => void detail.reload()} />;
  if (!detail.channel) return <LoadingState />;

  const { channel } = detail;
  if (!editor.draft) return <LoadingState />;
  const canEdit = hasCapability(user, "channels.manage");
  const canOpenAgent = hasCapability(user, "ai.view");
  const canOpenDialogs = hasCapability(user, "conversations.view");
  const editAccess = {
    name: canEdit,
    group: canEdit,
    product: canEdit,
    policy: canEdit,
  };
  const draftGroup = groups.find((item) => item.id === editor.draft!.groupId);
  const draftProduct = products.find((item) => item.id === editor.draft!.productId);

  async function saveDraft() {
    if (!editor.draft) return;
    const saved = await detail.patch(channelDraftRequest(editor.draft, editAccess));
    if (saved) editor.finish();
  }

  return (
    <div className="channel-detail">
      <ChannelDetailHeader
        channel={channel}
        canEdit={canEdit}
        editing={editor.editing}
        busy={detail.busy}
        onEdit={editor.begin}
        onSave={() => void saveDraft()}
        onCancel={editor.cancel}
      />

      {detail.feedback && <div className={`channel-feedback is-${detail.feedback.kind}`}>{detail.feedback.text}</div>}
      {!channel.isActive && <ChannelArchivedNotice name={channel.name} code={channel.code} />}

      <ChannelAssignmentSection
        channel={channel}
        groups={groups}
        products={products}
        editing={editor.editing}
        canEditName={canEdit}
        canEditGroup={canEdit}
        canEditProduct={canEdit}
        name={editor.draft.name}
        groupId={editor.draft.groupId}
        productId={editor.draft.productId}
        onNameChange={editor.setName}
        onGroupChange={editor.setGroupId}
        onProductChange={editor.setProductId}
      />

      <ChannelPolicySection
        policy={editor.draft.policy}
        hasProduct={editor.draft.productId !== null}
        productName={draftProduct?.name ?? "— непродуктовый"}
        groupName={draftGroup?.name ?? "Без группы"}
        editing={editor.editing}
        canManage={canEdit}
        busy={detail.busy}
        onToggle={(flag: PolicyFlag, value) => editor.setPolicy(flag, value)}
      />

      {!editor.editing && (
        <>
          <ChannelConnectionsSection
            channel={channel}
            canOpenIntegrations={hasCapability(user, "integrations.view")}
            openIntegrations={() => setRoute("integrations")}
          />
          <ChannelAgentSection channel={channel} canOpenAgent={canOpenAgent} openAgent={openAgent} openAgentCreate={() => setRoute("aiAgentCreate")} />
          <ChannelCountersSection channel={channel} canOpenDialogs={canOpenDialogs} openDialogs={() => setRoute("salesDialogs")} />
        </>
      )}

      {editor.editing && canEdit && (
        <ChannelDangerActions
          active={channel.isActive}
          busy={detail.busy}
          dirty={editor.dirty}
          onToggleActive={detail.requestToggleActive}
          onDelete={() => detail.setDeleting(true)}
        />
      )}

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

import type { ChannelUpdateInput } from "./api";
import type { Channel, ChannelPolicy, PolicyFlag } from "./types";

export type ChannelEditDraft = {
  name: string;
  groupId: number | null;
  productId: number | null;
  policy: ChannelPolicy;
};

export type ChannelEditAccess = {
  name: boolean;
  group: boolean;
  product: boolean;
  policy: boolean;
};

const PRODUCT_REQUIRED_FLAGS: PolicyFlag[] = [
  "requiresAuthenticatedProductIdentity",
  "allowSalesAttribution",
  "allowCheckoutActions",
];

export function channelDraft(channel: Channel): ChannelEditDraft {
  return {
    name: channel.name,
    groupId: channel.groupId,
    productId: channel.product?.id ?? null,
    policy: { ...channel.policy },
  };
}

export function channelDraftWithProduct(
  draft: ChannelEditDraft,
  productId: number | null,
): ChannelEditDraft {
  if (productId !== null) return { ...draft, productId };
  const policy = { ...draft.policy };
  PRODUCT_REQUIRED_FLAGS.forEach((flag) => {
    policy[flag] = false;
  });
  return { ...draft, productId, policy };
}

export function channelDraftRequest(
  draft: ChannelEditDraft,
  access: ChannelEditAccess,
): ChannelUpdateInput {
  return {
    ...(access.name ? { name: draft.name.trim() } : {}),
    ...(access.group ? { groupId: draft.groupId } : {}),
    ...(access.product ? { productId: draft.productId } : {}),
    ...(access.policy ? { policy: draft.policy } : {}),
  };
}

export function channelDraftChanged(channel: Channel, draft: ChannelEditDraft): boolean {
  return JSON.stringify(channelDraft(channel)) !== JSON.stringify(draft);
}

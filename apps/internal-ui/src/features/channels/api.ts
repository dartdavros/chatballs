import { api } from "../../api/client";
import type { Channel, ChannelPolicy, PolicyPreset } from "./types";

export type ChannelCreateInput = {
  code: string;
  name: string;
  departmentId: number | null;
  productId: number | null;
  policyPreset: PolicyPreset;
  policy?: ChannelPolicy;
};

export type ChannelUpdateInput = {
  name?: string;
  departmentId?: number | null;
  productId?: number | null;
  isActive?: boolean;
  policy?: Partial<ChannelPolicy>;
};

export type ChannelResponse = {
  channel: Channel;
  warnings?: { code: string; agentId: number }[];
};

export function listChannels(): Promise<{ items: Channel[] }> {
  return api("/api/v1/channels/");
}

export function loadChannel(channelId: number): Promise<{ channel: Channel }> {
  return api(`/api/v1/channels/${channelId}/`);
}

export function createChannel(input: ChannelCreateInput): Promise<{ channel: Channel }> {
  // policy передаётся только для CUSTOM: пресет и явная политика
  // взаимоисключающи (SPEC-HUB-0027 §6.3).
  const body: Record<string, unknown> = {
    code: input.code,
    name: input.name,
    departmentId: input.departmentId,
    productId: input.productId,
    policyPreset: input.policyPreset,
  };
  if (input.policyPreset === "CUSTOM") body.policy = input.policy;
  return api("/api/v1/channels/", { method: "POST", body: JSON.stringify(body) });
}

export function updateChannel(
  channelId: number,
  input: ChannelUpdateInput,
): Promise<ChannelResponse> {
  return api(`/api/v1/channels/${channelId}/`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function deleteChannel(channelId: number): Promise<void> {
  return api(`/api/v1/channels/${channelId}/`, { method: "DELETE" });
}

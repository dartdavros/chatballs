import { useEffect, useState } from "react";

import {
  channelDraft,
  channelDraftChanged,
  channelDraftWithProduct,
  type ChannelEditDraft,
} from "./channel-editor";
import type { Channel, PolicyFlag } from "./types";

export function useChannelEditor(channel: Channel | null) {
  const [editing, setEditing] = useState(false);
  const [storedDraft, setStoredDraft] = useState<ChannelEditDraft | null>(null);
  const draft = editing ? storedDraft : channel ? channelDraft(channel) : null;

  useEffect(() => {
    setEditing(false);
    setStoredDraft(null);
  }, [channel?.id]);

  function begin() {
    if (!channel) return;
    setStoredDraft(channelDraft(channel));
    setEditing(true);
  }

  function cancel() {
    setEditing(false);
    setStoredDraft(null);
  }

  function update(patch: Partial<ChannelEditDraft>) {
    setStoredDraft((current) => current ? { ...current, ...patch } : current);
  }

  function setProductId(productId: number | null) {
    setStoredDraft((current) => current ? channelDraftWithProduct(current, productId) : current);
  }

  function setPolicy(flag: PolicyFlag, value: boolean) {
    setStoredDraft((current) => current ? {
      ...current,
      policy: { ...current.policy, [flag]: value },
    } : current);
  }

  return {
    draft,
    dirty: Boolean(editing && channel && storedDraft && channelDraftChanged(channel, storedDraft)),
    editing,
    begin,
    cancel,
    finish: cancel,
    setGroupId: (groupId: number | null) => update({ groupId }),
    setName: (name: string) => update({ name }),
    setPolicy,
    setProductId,
  };
}

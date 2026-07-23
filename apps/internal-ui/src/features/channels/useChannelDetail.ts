import { useCallback, useEffect, useState } from "react";

import { ApiError } from "../../api/client";
import { deleteChannel, loadChannel, updateChannel } from "./api";
import type { Channel, DeletionBlocker, PolicyViolation } from "./types";

export type ChannelFeedback = { kind: "error" | "warning"; text: string } | null;

export function useChannelDetail(channelId: number | null, openChannels: () => void) {
  const [channel, setChannel] = useState<Channel | null>(null);
  const [missing, setMissing] = useState(false);
  const [loadFailed, setLoadFailed] = useState(false);
  const [feedback, setFeedback] = useState<ChannelFeedback>(null);
  const [busy, setBusy] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [confirmingDeactivation, setConfirmingDeactivation] = useState(false);
  const [blockers, setBlockers] = useState<DeletionBlocker[] | null>(null);

  const reload = useCallback(async () => {
    if (channelId === null) return;
    try {
      const response = await loadChannel(channelId);
      setChannel(response.channel);
      setMissing(false);
      setLoadFailed(false);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) setMissing(true);
      else setLoadFailed(true);
    }
  }, [channelId]);

  useEffect(() => {
    setChannel(null);
    setMissing(false);
    setLoadFailed(false);
    void reload();
  }, [reload]);

  async function patch(body: Parameters<typeof updateChannel>[1]) {
    if (!channel) return false;
    setFeedback(null);
    setBusy(true);
    try {
      const response = await updateChannel(channel.id, body);
      setChannel(response.channel);
      if (response.warnings?.some((item) => item.code === "agent_still_active")) {
        setFeedback({
          kind: "warning",
          text: "Канал деактивирован, но агент остаётся активным и продолжает занимать слот. Остановите его на странице агента.",
        });
      }
      return true;
    } catch (error) {
      if (error instanceof ApiError) {
        const violations = (error.payload as { violations?: PolicyViolation[] }).violations;
        setFeedback({
          kind: "error",
          text: violations?.length ? violations.map((item) => item.detail).join("; ") : error.message,
        });
      } else setFeedback({ kind: "error", text: "Не удалось сохранить канал." });
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!channel) return;
    setBusy(true);
    try {
      await deleteChannel(channel.id);
      openChannels();
    } catch (error) {
      if (error instanceof ApiError) {
        const payload = error.payload as { blockers?: DeletionBlocker[] };
        if (payload.blockers) setBlockers(payload.blockers);
        else {
          setDeleting(false);
          setFeedback({ kind: "error", text: error.message });
        }
      } else setFeedback({ kind: "error", text: "Не удалось удалить канал." });
    } finally {
      setBusy(false);
    }
  }

  function closeDeleteDialog() {
    setDeleting(false);
    setBlockers(null);
  }

  function requestToggleActive() {
    if (!channel) return;
    if (channel.isActive && channel.agent?.status === "ACTIVE") setConfirmingDeactivation(true);
    else void patch({ isActive: !channel.isActive });
  }

  return {
    blockers, busy, channel, confirmingDeactivation, deleting, feedback, loadFailed, missing,
    closeDeleteDialog, patch, reload, remove, requestToggleActive, setChannel, setConfirmingDeactivation,
    setDeleting,
  };
}

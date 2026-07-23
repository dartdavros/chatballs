import { useCallback, useEffect, useMemo, useState } from "react";

import { ApiError } from "../../api/client";
import { deleteChannel, listChannels, updateChannel } from "./api";
import { departmentTabs, filterChannels } from "./model";
import type { Channel, DeletionBlocker } from "./types";

export function useChannelsPage(departments: Array<{ id: number; name: string; code?: string }>) {
  const [channels, setChannels] = useState<Channel[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [tab, setTab] = useState("all");
  const [search, setSearch] = useState("");
  const [showArchived, setShowArchived] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Channel | null>(null);
  const [deactivationTarget, setDeactivationTarget] = useState<Channel | null>(null);
  const [blockers, setBlockers] = useState<DeletionBlocker[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      const response = await listChannels();
      setChannels(response.items);
      setFailed(false);
    } catch {
      setFailed(true);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const tabs = useMemo(() => departmentTabs(channels ?? [], departments), [channels, departments]);
  const visible = useMemo(
    () => filterChannels(channels ?? [], { tab, search, showArchived }),
    [channels, tab, search, showArchived],
  );

  async function toggleActive(channel: Channel) {
    setBusy(true);
    setFeedback(null);
    try {
      await updateChannel(channel.id, { isActive: !channel.isActive });
      await reload();
    } catch (error) {
      setFeedback(error instanceof ApiError ? error.message : "Не удалось изменить состояние канала.");
    } finally {
      setBusy(false);
    }
  }

  function requestToggleActive(channel: Channel) {
    if (channel.isActive && channel.agent?.status === "ACTIVE") setDeactivationTarget(channel);
    else void toggleActive(channel);
  }

  async function removeChannel(channel: Channel) {
    setBusy(true);
    setFeedback(null);
    try {
      await deleteChannel(channel.id);
      closeDelete();
      await reload();
    } catch (error) {
      const payload = (error as { payload?: { blockers?: DeletionBlocker[] } }).payload;
      if (payload?.blockers) setBlockers(payload.blockers);
      else {
        closeDelete();
        setFeedback(error instanceof ApiError ? error.message : "Не удалось удалить канал.");
      }
    } finally {
      setBusy(false);
    }
  }

  function closeDelete() {
    setDeleteTarget(null);
    setBlockers(null);
  }

  return {
    archived: channels?.filter((channel) => !channel.isActive).length ?? 0,
    blockers, busy, channels, deactivationTarget, deleteTarget, failed, feedback, search, showArchived, tab, tabs, visible,
    closeDelete, reload, removeChannel, requestToggleActive, setDeactivationTarget, setDeleteTarget,
    setSearch, setShowArchived, setTab, toggleActive,
  };
}

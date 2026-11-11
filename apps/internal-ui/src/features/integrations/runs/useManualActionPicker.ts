import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../../../api/client";
import { t } from "../../../i18n";
import { actionKey } from "./actionPickerModel";
import { getManualAction, getManualActions } from "./api";
import type { ManualActionDetail, ManualActionSummary } from "./types";

/** Lives only while the picker is open; closing invalidates both requests. */
export function useManualActionPicker(conversationId: number, onSelected: (detail: ManualActionDetail) => void) {
  const [items, setItems] = useState<ManualActionSummary[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [catalogError, setCatalogError] = useState("");
  const [actionError, setActionError] = useState("");
  const [pendingKey, setPendingKey] = useState<string | null>(null);
  const active = useRef(false);
  const requests = useRef<{ catalog?: AbortController; detail?: AbortController }>({});
  const contextRef = useRef({ conversationId });
  if (contextRef.current.conversationId !== conversationId) contextRef.current = { conversationId };
  const context = contextRef.current;
  const selected = useRef(onSelected);
  selected.current = onSelected;
  const dismiss = useCallback(() => {
    active.current = false;
    requests.current.catalog?.abort();
    requests.current.detail?.abort();
  }, []);
  const reload = useCallback(async () => {
    requests.current.catalog?.abort();
    const request = new AbortController();
    requests.current.catalog = request;
    setLoading(true); setCatalogError(""); setItems(null);
    try {
      const catalog = await getManualActions(conversationId, request.signal);
      if (active.current && contextRef.current === context && !request.signal.aborted) setItems(catalog.items.filter(item => item.available === true));
    } catch (error) {
      if (active.current && contextRef.current === context && !request.signal.aborted) setCatalogError(error instanceof ApiError ? error.message : t("run_action_picker.load_failed"));
    } finally { if (active.current && contextRef.current === context && !request.signal.aborted) setLoading(false); }
  }, [conversationId, context]);
  useEffect(() => {
    active.current = true;
    void reload();
    return dismiss;
  }, [dismiss, reload]);
  const choose = async (action: ManualActionSummary) => {
    if (!active.current || contextRef.current !== context || action.available !== true || loading) return;
    requests.current.detail?.abort();
    const request = new AbortController();
    requests.current.detail = request;
    setPendingKey(actionKey(action)); setActionError("");
    try {
      const detail = await getManualAction(conversationId, action, request.signal);
      if (!active.current || contextRef.current !== context || request.signal.aborted) return;
      if (detail.item.available !== true || actionKey(detail.item) !== actionKey(action)) throw new ApiError(409, { detail: t("runs.unavailable") });
      dismiss();
      selected.current(detail);
    } catch (error) {
      if (!active.current || contextRef.current !== context || request.signal.aborted) return;
      setActionError(error instanceof ApiError ? error.message : t("run_action_picker.action_failed"));
      if (error instanceof ApiError && [403, 404, 409].includes(error.status)) {
        setItems(current => current?.filter(item => actionKey(item) !== actionKey(action)) ?? null);
        void reload();
      }
    } finally { if (active.current && contextRef.current === context && !request.signal.aborted) setPendingKey(null); }
  };
  return { items, loading, catalogError, actionError, pendingKey, reload, choose, dismiss };
}

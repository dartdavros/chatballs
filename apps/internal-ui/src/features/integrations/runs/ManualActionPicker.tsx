import { Modal } from "antd";
import { useEffect, useMemo, useRef, useState } from "react";
import { fmt, t, tn } from "../../../i18n";
import { Icon } from "../../../shared/icons";
import { LoadingState } from "../../../shared/ui";
import { Button, SearchInput } from "../../../shared/ui-controls";
import { actionSearchWords, buildActionPickerGroups } from "./actionPickerModel";
import { ActionPickerTree } from "./ActionPickerTree";
import type { ManualActionDetail } from "./types";
import { useManualActionPicker } from "./useManualActionPicker";
import "./manual-action-menu.css";

export function ManualActionPicker({ conversationId, conversationTitle, onClose, onSelected }: {
  conversationId: number; conversationTitle?: string; onClose: () => void; onSelected: (detail: ManualActionDetail) => void;
}) {
  const state = useManualActionPicker(conversationId, onSelected);
  const close = () => { state.dismiss(); onClose(); };
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set());
  const [collapsedSearch, setCollapsedSearch] = useState<Set<string>>(() => new Set());
  const initialized = useRef(false);
  const searchRef = useRef<HTMLInputElement>(null);
  const groups = useMemo(() => buildActionPickerGroups(state.items ?? [], search), [state.items, search]);
  const searching = actionSearchWords(search).length > 0;
  const count = groups.reduce((total, group) => total + group.count, 0);
  useEffect(() => {
    if (initialized.current || !state.items) return;
    initialized.current = true;
    const defaults = new Set<string>();
    let first = buildActionPickerGroups(state.items)[0];
    while (first) { defaults.add(first.key); first = first.groups[0]; }
    setExpanded(defaults);
  }, [state.items]);
  const changeSearch = (value: string) => { setSearch(value); setCollapsedSearch(new Set()); };
  const toggle = (key: string) => {
    const update = searching ? setCollapsedSearch : setExpanded;
    update(current => { const next = new Set(current); if (next.has(key)) next.delete(key); else next.add(key); return next; });
  };
  const context = [conversationTitle, t("runs.conversation", { number: fmt.number(conversationId) })].filter(Boolean).join(" · ");
  return <Modal className="agent-knowledge-modal manual-action-picker" open width={680} centered destroyOnHidden
    title={<div><strong>{t("run_action_picker.title")}</strong><p className="manual-action-context">{context}</p></div>}
    onCancel={close} afterOpenChange={open => { if (open) searchRef.current?.focus(); }}
    footer={<div className="manual-action-picker-footer"><span role="status" aria-live="polite">{state.loading ? t("runs.loading")
      : !state.catalogError ? tn(searching ? "run_action_picker.found" : "run_action_picker.available", count) : ""}</span>
      <Button variant="secondary" onClick={close}>{t("common.cancel")}</Button></div>}>
    <SearchInput className="manual-action-search" inputRef={searchRef} clearable placeholder={t("run_action_picker.search")} value={search} onChange={changeSearch} />
    <div className="manual-action-catalog" aria-busy={state.loading || state.pendingKey !== null}>
      {(state.catalogError || state.actionError) && <div className="run-notice is-error" role="alert">
        {state.catalogError || state.actionError}
        {state.catalogError && <button type="button" className="link" onClick={() => void state.reload()}>{t("runs.retry")}</button>}
      </div>}
      {state.loading ? <LoadingState /> : !state.catalogError && (count > 0
        ? <ActionPickerTree groups={groups} search={search} expanded={expanded} collapsedSearch={collapsedSearch}
          pendingKey={state.pendingKey} onToggle={toggle} onSelect={action => void state.choose(action)} />
        : <div className="manual-action-empty"><Icon name="search" size={25} />
          <strong>{searching && state.items?.length ? t("common.nothing_found") : t("runs.no_actions")}</strong>
          <p>{searching && state.items?.length ? t("run_action_picker.no_results") : t("run_action_picker.empty")}</p>
          {searching && <Button variant="secondary" onClick={() => { changeSearch(""); searchRef.current?.focus(); }}>{t("shared.clear_search")}</Button>}
        </div>)}
    </div>
  </Modal>;
}

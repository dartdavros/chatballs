import { Modal } from "antd";
import { useMemo, useState } from "react";
import { t, fmt } from "../../../i18n";
import { DecisionDialog } from "../../../shared/DecisionDialog";
import { Icon } from "../../../shared/icons";
import { LoadingState } from "../../../shared/ui";
import { Button, SearchInput } from "../../../shared/ui-controls";
import { AgentActionRow } from "./AgentActionRow";
import { groupActions } from "./catalogGroups";
import type { useAgentActions } from "./useAgentActions";

export function AgentActionsDialog({ state, onClose }: {
  state: ReturnType<typeof useAgentActions>; onClose: () => void;
}) {
  const [search, setSearch] = useState("");
  const [closed, setClosed] = useState<Set<string>>(() => new Set());
  const [leaving, setLeaving] = useState(false);
  const groups = useMemo(() => groupActions(state.rows ?? [], search), [state.rows, search]);
  const close = () => { if (!state.busy) { if (state.dirty) setLeaving(true); else onClose(); } };
  const discard = () => { state.reset(); onClose(); };
  const save = async () => { if (await state.save()) onClose(); else setLeaving(false); };
  return <>
    <Modal className="agent-knowledge-modal agent-actions-modal" open width={800} title={t("agent_actions.title")}
      onCancel={close} footer={null} destroyOnHidden>
      <SearchInput className="agent-knowledge-search" placeholder={t("agent_actions.search")} value={search} onChange={setSearch} />
      {state.error && <div className="run-notice is-error" role="alert">{state.error}<button type="button" className="link" disabled={state.busy} onClick={() => void state.reload()}>{t("runs.retry")}</button></div>}
      <div className="agent-knowledge-choices agent-actions-body">
        {!state.rows && !state.error && <LoadingState />}
        {state.rows?.length === 0 && <p className="agent-actions-empty">{t("agent_actions.empty")}</p>}
        {!!state.rows?.length && groups.length === 0 && <p className="agent-knowledge-nothing">{t("common.nothing_found")}</p>}
        {groups.map(group => {
          const open = Boolean(search.trim()) || !closed.has(group.key);
          return <div className="agent-knowledge-group" key={group.key}>
            <div className="agent-knowledge-group-head">
              <button type="button" className={`agent-knowledge-group-toggle${open ? " is-open" : ""}`} aria-expanded={open}
                onClick={() => setClosed(current => { const next = new Set(current); if (next.has(group.key)) next.delete(group.key); else next.add(group.key); return next; })}>
                <Icon name="chevronRight" size={13} strokeWidth={2.2} /><strong>{group.title}</strong><small>{fmt.number(group.rows.length)}</small>
              </button>
            </div>
            {open && group.rows.map(row => <AgentActionRow key={row.id} row={row} busy={state.busy} change={state.change} />)}
          </div>;
        })}
      </div>
      <p className="agent-actions-foot">{t("agent_actions.applies")}</p>
      <div className="agent-create-actions">
        <Button variant="secondary" disabled={state.busy} onClick={close}>{t("common.cancel")}</Button>
        <Button variant="primary" disabled={!state.rows || !state.dirty || state.busy} onClick={() => void save()}>{state.busy ? t("ai.saving") : t("common.save")}</Button>
      </div>
    </Modal>
    <DecisionDialog open={leaving} tone="warning" icon="warning" title={t("agent_actions.leave")} description={t("skills.leave_hint")}
      onClose={() => setLeaving(false)} actions={<>
        <Button variant="secondary" disabled={state.busy} onClick={discard}>{t("skills.discard")}</Button>
        <Button variant="secondary" disabled={state.busy} onClick={() => setLeaving(false)}>{t("skills.stay")}</Button>
        <Button variant="primary" disabled={state.busy} onClick={() => void save()}>{t("common.save")}</Button>
      </>} />
  </>;
}

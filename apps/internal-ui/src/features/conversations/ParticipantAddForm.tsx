import { useState } from "react";
import { SmallAvatar } from "./assigneeOptions";
import { WorkStatusLabel } from "../work-status/WorkStatusLabel";
import { useEmployeeDirectory } from "./useEmployeeDirectory";
import { Button, SearchInput } from "../../shared/ui-controls";
import { Icon } from "../../shared/icons";
import { t } from "../../i18n";
import type { ApiParticipant } from "./participantApi";
import type { ChatDirectoryEmployee } from "./conversationApi";

export function ParticipantAddForm({ current, assigneeId, busy, failed, onCancel, onSubmit }: {
  current: ApiParticipant[]; assigneeId: number | null; busy: boolean; failed: boolean;
  onCancel: () => void; onSubmit: (id: number, name: string, reason: string) => Promise<boolean>;
}) {
  const directory = useEmployeeDirectory();
  const [selected, setSelected] = useState<ChatDirectoryEmployee | null>(null);
  const [reason, setReason] = useState("");
  const [required, setRequired] = useState(false);
  const excluded = new Set(current.map((row) => row.membershipId));
  const employees = directory.employees.filter((row) => row.id !== assigneeId && !excluded.has(row.membershipId));
  async function submit() {
    if (!reason.trim()) { setRequired(true); return; }
    if (selected) await onSubmit(selected.membershipId, selected.name, reason);
  }
  return (
    <div className="participant-add-form" data-search-scope>
      <SearchInput value={directory.query} onChange={directory.setQuery} placeholder={t("participants.search")} />
      {directory.errorText && <div className="participant-banner" role="alert">{directory.errorText}</div>}
      <div className="participant-options">
        {employees.map((employee) => <button type="button" key={employee.membershipId}
          className={`participant-option ${selected?.membershipId === employee.membershipId ? "is-selected" : ""}`}
          disabled={busy} onClick={() => setSelected(employee)}>
          <SmallAvatar name={employee.name} avatarUrl={employee.avatarUrl} online={employee.online} />
          <span><strong>{employee.name}</strong><small><WorkStatusLabel value={employee.workStatus} /> · {t("conversations.open_dialogs", { count: employee.openDialogs ?? 0 })}</small></span>
          {selected?.membershipId === employee.membershipId && <Icon name="check" size={14} />}
        </button>)}
      </div>
      <label className="participant-reason-label">{t("participants.reason_label")}
        <textarea value={reason} disabled={busy} aria-invalid={required && !reason.trim()} onChange={(event) => { setReason(event.target.value); setRequired(false); }} />
      </label>
      {required && !reason.trim() && <small className="participant-field-error">{t("participants.reason_required")}</small>}
      <small className="participant-help">{t("participants.reason_note")}</small>
      <footer><Button variant="secondary" disabled={busy} onClick={onCancel}>{t("common.cancel")}</Button>
        <Button variant="primary" disabled={busy || !selected} onClick={() => void submit()}>{t(failed ? "common.try_again" : "participants.connect")}</Button></footer>
    </div>
  );
}

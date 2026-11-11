import { t, tn } from "../../i18n";
import type { ChatDirectoryEmployee } from "../conversations/model";
import { SearchInput } from "../../shared/ui-controls";
import { useMediaQuery } from "../../shared/useMediaQuery";
import { WorkStatusBadge } from "./WorkStatusBadge";
import { recipientPresence, TransferRecipientAvatar } from "./TransferRecipientPerson";
import { MobileTransferRecipients } from "./MobileTransferRecipients";

export type TransferRecipientsProps = {
  people: ChatDirectoryEmployee[]; recipient: number | null; query: string;
  onQuery: (value: string) => void; onChoose: (id: number) => void; disabled: boolean;
};
export function TransferRecipients(props: TransferRecipientsProps) {
  const mobile = useMediaQuery("(max-width: 600px)");
  const { people, recipient, query, onQuery, onChoose, disabled } = props;
  if (mobile) return <MobileTransferRecipients {...props} />;
  return <div className="transfer-recipient-picker">
    <label className="transfer-field-label" htmlFor="transfer-search">{t("transfers.to")}</label>
    <SearchInput className="transfer-search" id="transfer-search" placeholder={t("transfers.search")} value={query} disabled={disabled} onChange={onQuery} />
    <div className="transfer-recipients">
      <div className="transfer-recipient-row is-heading"><span>{t("transfers.employee")}</span><span>{t("transfers.work_status")}</span><span>{t("transfers.load")}</span><span /></div>
      <div className="transfer-recipient-list">
        {[true, false].map((allowed) => <div key={String(allowed)}>
          <div className="transfer-recipient-group">{t(allowed ? "transfers.allowed" : "transfers.forbidden")}</div>
          {people.filter((person) => person.assignmentAllowed === allowed).map((person) =>
            <button type="button" key={person.id} className={`transfer-recipient-row ${recipient === person.id ? "is-selected" : ""}`}
              disabled={disabled || !allowed} onClick={() => onChoose(person.id)}
              aria-pressed={recipient === person.id} title={!allowed ? t("transfers.status_forbidden") : undefined}>
              <span className="transfer-person">
                <TransferRecipientAvatar person={person} />
                <span><strong>{person.name}</strong><small>{recipientPresence(person)}</small></span>
              </span>
              <WorkStatusBadge status={person.workStatus.status} />
              <span className="transfer-load">{tn("transfers.dialog_count", person.openDialogs ?? 0)}</span>
              <i className="transfer-radio" aria-hidden="true">{recipient === person.id && <b />}</i>
            </button>)}
        </div>)}
      </div>
      <p>{t("transfers.directory_note")}</p>
    </div>
  </div>;
}

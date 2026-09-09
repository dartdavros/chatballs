import { useState } from "react";

import { DecisionDialog } from "../../../shared/DecisionDialog";
import { Button } from "../../../shared/ui-controls";
import type { ClientDetailVm } from "./model";
import { t } from "../../../i18n";

// Сравнение и объединение контактов (ADR-CHATBALLS-0006, кадр K5): владелец видит,
// что именно переедет, и обязан указать причину — она попадёт в журнал.

export function SalesClientMergeDialog({ client, open, saving, error, onClose, onMerge }: {
  client: ClientDetailVm;
  open: boolean;
  saving: boolean;
  error: string;
  onClose: () => void;
  onMerge: (reason: string) => void;
}) {
  const [reason, setReason] = useState("");
  const duplicate = client.duplicate;
  if (!duplicate) return null;

  return (
    <DecisionDialog
      open={open}
      onClose={onClose}
      tone="warning"
      icon="transfer"
      title={t("sales.merge_contacts")}
      description={t("sales.identities_conversations_move_contact_stays")}
      className="sales-client-merge-dialog"
      width={620}
      actions={(
        <>
          <Button variant="secondary" onClick={onClose}>{t("common.cancel")}</Button>
          <Button variant="primary" disabled={saving || reason.trim().length < 5} onClick={() => onMerge(reason)}>
            {saving ? t("sales.merging") : t("sales.merge")}
          </Button>
        </>
      )}
    >
      <div className="sales-client-merge-compare">
        <div>
          <small>{t("sales.stays")}</small>
          <strong>{client.name}</strong>
          <span>{client.cid}</span>
          <span>{client.phone || t("sales.no_phone_number")}</span>
          <span>{t("sales.identities_and_dialogs", { identities: client.identities.length, dialogs: client.totalDialogs })}</span>
        </div>
        <div className="is-source">
          <small>{t("sales.merged")}</small>
          <strong>{duplicate.name}</strong>
          <span>{duplicate.cid}</span>
          <span>{duplicate.phone || t("sales.no_phone_number")}</span>
          <span>{duplicate.sourceLabel}</span>
        </div>
      </div>
      <label className="sales-client-merge-reason">
        <span>{t("sales.reason_merging")}</span>
        <textarea
          rows={3}
          maxLength={2000}
          placeholder={t("sales.example_same_customer_confirmed_phone")}
          value={reason}
          onChange={(event) => setReason(event.target.value)}
        />
      </label>
      {error && <div className="sales-client-merge-error">{error}</div>}
    </DecisionDialog>
  );
}

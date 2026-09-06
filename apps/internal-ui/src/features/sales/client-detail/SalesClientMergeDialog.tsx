import { useState } from "react";

import { DecisionDialog } from "../../../shared/DecisionDialog";
import { Button } from "../../../shared/ui-controls";
import type { ClientDetailVm } from "./model";

// Сравнение и объединение контактов (ADR-HUB-0006, кадр K5): владелец видит,
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
      title="Объединить контакты"
      description="Идентичности и диалоги перейдут к контакту, который останется. Операция записывается в журнал действий и может быть разъединена обратно."
      className="sales-client-merge-dialog"
      width={620}
      actions={(
        <>
          <Button variant="secondary" onClick={onClose}>Отмена</Button>
          <Button variant="primary" disabled={saving || reason.trim().length < 5} onClick={() => onMerge(reason)}>
            {saving ? "Объединение" : "Объединить"}
          </Button>
        </>
      )}
    >
      <div className="sales-client-merge-compare">
        <div>
          <small>Останется</small>
          <strong>{client.name}</strong>
          <span>{client.cid}</span>
          <span>{client.phone || "телефон не указан"}</span>
          <span>{client.identities.length} идентичн. · {client.totalDialogs} диал.</span>
        </div>
        <div className="is-source">
          <small>Присоединяется</small>
          <strong>{duplicate.name}</strong>
          <span>{duplicate.cid}</span>
          <span>{duplicate.phone || "телефон не указан"}</span>
          <span>{duplicate.sourceLabel}</span>
        </div>
      </div>
      <label className="sales-client-merge-reason">
        <span>Причина объединения</span>
        <textarea
          rows={3}
          maxLength={2000}
          placeholder="Например: один и тот же клиент, совпал подтверждённый телефон"
          value={reason}
          onChange={(event) => setReason(event.target.value)}
        />
      </label>
      {error && <div className="sales-client-merge-error">{error}</div>}
    </DecisionDialog>
  );
}

// Разъединение: тоже с причиной и записью в журнал.
export function SalesClientUnmergeDialog({ merge, open, saving, error, onClose, onRevert }: {
  merge: ClientDetailVm["merges"][number] | null;
  open: boolean;
  saving: boolean;
  error: string;
  onClose: () => void;
  onRevert: (reason: string) => void;
}) {
  const [reason, setReason] = useState("");
  if (!merge) return null;
  return (
    <DecisionDialog
      open={open}
      onClose={onClose}
      tone="warning"
      icon="transfer"
      title="Разъединить контакты"
      description={`Идентичности и диалоги вернутся контакту «${merge.sourceName}». Операция записывается в журнал действий.`}
      className="sales-client-merge-dialog"
      actions={(
        <>
          <Button variant="secondary" onClick={onClose}>Отмена</Button>
          <Button variant="danger-outline" disabled={saving || reason.trim().length < 5} onClick={() => onRevert(reason)}>
            {saving ? "Разъединение" : "Разъединить"}
          </Button>
        </>
      )}
    >
      <label className="sales-client-merge-reason">
        <span>Причина разъединения</span>
        <textarea
          rows={3}
          maxLength={2000}
          placeholder="Например: это разные люди, объединили по ошибке"
          value={reason}
          onChange={(event) => setReason(event.target.value)}
        />
      </label>
      {error && <div className="sales-client-merge-error">{error}</div>}
    </DecisionDialog>
  );
}

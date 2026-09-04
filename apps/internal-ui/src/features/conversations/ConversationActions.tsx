import { Dropdown } from "antd";
import { useState } from "react";

import { DecisionDialog } from "../../shared/DecisionDialog";
import { Icon } from "../../shared/icons";
import { Button } from "../../shared/ui-controls";

export function ConversationActions({
  open,
  canReturnQueue,
  onClose,
  onSpam,
  onReturnQueue,
  onArchive,
}: {
  open: boolean;
  canReturnQueue: boolean;
  onClose: () => void;
  onSpam: () => Promise<boolean>;
  onReturnQueue: () => void;
  onArchive: () => Promise<boolean>;
}) {
  const [confirmSpam, setConfirmSpam] = useState(false);
  const [confirmArchive, setConfirmArchive] = useState(false);
  const [busy, setBusy] = useState(false);

  if (!open) return null;

  async function confirm() {
    setBusy(true);
    try {
      if (await onSpam()) setConfirmSpam(false);
    } finally {
      setBusy(false);
    }
  }

  async function confirmArchiveAction() {
    setBusy(true);
    try {
      if (await onArchive()) setConfirmArchive(false);
    } finally {
      setBusy(false);
    }
  }

  const items = [
    ...(canReturnQueue
      ? [{
          key: "queue",
          label: <button type="button" onClick={onReturnQueue}><Icon name="refresh" size={15} />Вернуть в очередь</button>,
        }]
      : []),
    {
      key: "close",
      label: <button type="button" onClick={onClose}><Icon name="lock" size={15} />Закрыть диалог</button>,
    },
    { type: "divider" as const },
    {
      key: "spam",
      label: <button className="danger" type="button" onClick={() => setConfirmSpam(true)}><Icon name="warning" size={15} />Пометить как спам</button>,
    },
    {
      key: "archive",
      label: <button className="danger" type="button" onClick={() => setConfirmArchive(true)}><Icon name="trash" size={15} />Удалить диалог</button>,
    },
  ];

  return (
    <>
      <Dropdown menu={{ items }} trigger={["click"]} placement="bottomRight" overlayClassName="app-dropdown">
        <button className="sales-more-button row-menu-button" type="button" aria-label="Действия диалога"><Icon name="more" size={18} /></button>
      </Dropdown>
      <DecisionDialog
        open={confirmSpam}
        onClose={() => !busy && setConfirmSpam(false)}
        tone="danger"
        icon="warning"
        title="Пометить диалог как спам?"
        description="Диалог будет закрыт для ответов и останется в истории со статусом «Спам»."
        actions={<>
          <Button variant="secondary" disabled={busy} onClick={() => setConfirmSpam(false)}>Отмена</Button>
          <Button variant="danger-outline" icon="warning" disabled={busy} onClick={() => void confirm()}>Пометить как спам</Button>
        </>}
      />
      <DecisionDialog
        open={confirmArchive}
        onClose={() => !busy && setConfirmArchive(false)}
        tone="danger"
        icon="trash"
        title="Удалить диалог?"
        description="Диалог уйдёт в архив и исчезнет из списков. Архив видят только администраторы."
        actions={<>
          <Button variant="secondary" disabled={busy} onClick={() => setConfirmArchive(false)}>Отмена</Button>
          <Button variant="danger-outline" icon="trash" disabled={busy} onClick={() => void confirmArchiveAction()}>Удалить</Button>
        </>}
      />
    </>
  );
}

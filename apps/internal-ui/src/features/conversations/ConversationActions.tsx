import { Dropdown } from "antd";
import { useState } from "react";

import { DecisionDialog } from "../../shared/DecisionDialog";
import { Icon } from "../../shared/icons";
import { Button } from "../../shared/ui-controls";

export function ConversationActions({
  open,
  onClose,
  onSpam,
}: {
  open: boolean;
  onClose: () => void;
  onSpam: () => Promise<boolean>;
}) {
  const [confirmSpam, setConfirmSpam] = useState(false);
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

  const items = [
    {
      key: "close",
      label: <button type="button" onClick={onClose}><Icon name="lock" size={15} />Закрыть диалог</button>,
    },
    { type: "divider" as const },
    {
      key: "spam",
      label: <button className="danger" type="button" onClick={() => setConfirmSpam(true)}><Icon name="warning" size={15} />Пометить как спам</button>,
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
    </>
  );
}

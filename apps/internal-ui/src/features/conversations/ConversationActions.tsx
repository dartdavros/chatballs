import { Dropdown } from "antd";
import { useState } from "react";

import { DecisionDialog } from "../../shared/DecisionDialog";
import { Icon } from "../../shared/icons";
import { Button } from "../../shared/ui-controls";
import { t } from "../../i18n";

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
          label: <button type="button" onClick={onReturnQueue}><Icon name="refresh" size={15} />{t("conversations.return_queue")}</button>,
        }]
      : []),
    {
      key: "close",
      label: <button type="button" onClick={onClose}><Icon name="lock" size={15} />{t("conversations.close_conversation")}</button>,
    },
    { type: "divider" as const },
    {
      key: "spam",
      label: <button className="danger" type="button" onClick={() => setConfirmSpam(true)}><Icon name="warning" size={15} />{t("conversations.mark_as_spam")}</button>,
    },
    {
      key: "archive",
      label: <button className="danger" type="button" onClick={() => setConfirmArchive(true)}><Icon name="trash" size={15} />{t("conversations.delete_conversation")}</button>,
    },
  ];

  return (
    <>
      <Dropdown menu={{ items }} trigger={["click"]} placement="bottomRight" overlayClassName="app-dropdown">
        <button className="sales-more-button row-menu-button" type="button" aria-label={t("conversations.conversation_actions")}><Icon name="more" size={18} /></button>
      </Dropdown>
      <DecisionDialog
        open={confirmSpam}
        onClose={() => !busy && setConfirmSpam(false)}
        tone="danger"
        icon="warning"
        title={t("conversations.mark_conversation_as_spam")}
        description={t("conversations.conversation_will_closed_replies_stay")}
        actions={<>
          <Button variant="secondary" disabled={busy} onClick={() => setConfirmSpam(false)}>{t("common.cancel")}</Button>
          <Button variant="danger-outline" icon="warning" disabled={busy} onClick={() => void confirm()}>{t("conversations.mark_as_spam")}</Button>
        </>}
      />
      <DecisionDialog
        open={confirmArchive}
        onClose={() => !busy && setConfirmArchive(false)}
        tone="danger"
        icon="trash"
        title={t("conversations.delete_conversation_2")}
        description={t("conversations.conversation_moves_archive_leaves_lists")}
        actions={<>
          <Button variant="secondary" disabled={busy} onClick={() => setConfirmArchive(false)}>{t("common.cancel")}</Button>
          <Button variant="danger-outline" icon="trash" disabled={busy} onClick={() => void confirmArchiveAction()}>{t("common.delete")}</Button>
        </>}
      />
    </>
  );
}

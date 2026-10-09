import { Dropdown } from "antd";
import { useState } from "react";

import { DecisionDialog } from "../../shared/DecisionDialog";
import { Icon } from "../../shared/icons";
import { Button } from "../../shared/ui-controls";
import { t } from "../../i18n";
import { useDiagnosticDownload } from "./useDiagnosticDownload";

// Меню «⋯» над перепиской: вернуть в очередь, закрыть, спам, удалить.
// Удаление стирает диалог вместе с перепиской и доступно только владельцу и
// администратору — у оператора этого пункта в меню нет.

export function ConversationActions({
  open,
  canReturnQueue,
  canDelete,
  onClose,
  onSpam,
  onReturnQueue,
  onDelete,
  conversationId,
  canExportDiagnostics,
  onDiagnosticError,
}: {
  open: boolean;
  canReturnQueue: boolean;
  canDelete: boolean;
  onClose: () => void;
  onSpam: () => Promise<boolean>;
  onReturnQueue: () => void;
  onDelete: () => Promise<boolean>;
  conversationId: number;
  canExportDiagnostics: boolean;
  onDiagnosticError: (error: string) => void;
}) {
  const [confirmSpam, setConfirmSpam] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [busy, setBusy] = useState(false);
  const { downloading, download } = useDiagnosticDownload(conversationId, onDiagnosticError);

  if (!open && !canExportDiagnostics) return null;

  async function confirm() {
    setBusy(true);
    try {
      if (await onSpam()) setConfirmSpam(false);
    } finally {
      setBusy(false);
    }
  }

  async function confirmDeleteAction() {
    setBusy(true);
    try {
      if (await onDelete()) setConfirmDelete(false);
    } finally {
      setBusy(false);
    }
  }

  const lifecycleItems = [
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
    ...(canDelete
      ? [{
          key: "delete",
          label: <button className="danger" type="button" onClick={() => setConfirmDelete(true)}><Icon name="trash" size={15} />{t("conversations.delete_conversation")}</button>,
        }]
      : []),
  ];
  const items = [
    ...(open ? lifecycleItems : []),
    ...(canExportDiagnostics ? [{
      key: "diagnostics", disabled: downloading,
      label: <button type="button" disabled={downloading} onClick={() => void download()}><Icon name="download" size={15} />{t("diagnostics.download")}</button>,
    }] : []),
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
        open={confirmDelete}
        onClose={() => !busy && setConfirmDelete(false)}
        tone="danger"
        icon="trash"
        title={t("conversations.delete_conversation_2")}
        description={t("conversations.conversation_and_history_gone_forever")}
        actions={<>
          <Button variant="secondary" disabled={busy} onClick={() => setConfirmDelete(false)}>{t("common.cancel")}</Button>
          <Button variant="danger-outline" icon="trash" disabled={busy} onClick={() => void confirmDeleteAction()}>{t("common.delete")}</Button>
        </>}
      />
    </>
  );
}

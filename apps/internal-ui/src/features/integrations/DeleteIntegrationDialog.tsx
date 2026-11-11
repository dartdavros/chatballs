import { Modal } from "antd";
import { useState } from "react";

import { api } from "../../api/client";
import { t } from "../../i18n";
import { Button } from "../../shared/ui-controls";
import type { Integration } from "./model";

export function DeleteIntegrationDialog({ integration, onClose, onDeleted }: {
  integration: Integration;
  onClose: () => void;
  onDeleted: () => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function confirmDelete() {
    setBusy(true);
    setError(null);
    try {
      await api(`/api/v1/integrations/${integration.id}/`, { method: "DELETE" });
      onDeleted();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : t("settings.could_not_delete"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open title={t("services.delete_title")} onCancel={onClose} footer={null} destroyOnClose>
      <div className="integration-form">
        <p>{t("settings.will_be_deleted_irreversible", { name: integration.name })}</p>
        {error && <div className="integration-form-error">{error}</div>}
        <div className="integration-form-actions">
          <Button variant="secondary" disabled={busy} onClick={onClose}>{t("common.cancel")}</Button>
          <Button variant="danger-outline" disabled={busy} onClick={() => void confirmDelete()}>{t("common.delete")}</Button>
        </div>
      </div>
    </Modal>
  );
}

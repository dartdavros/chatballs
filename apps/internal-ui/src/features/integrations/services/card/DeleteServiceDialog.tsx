import { useState } from "react";

import { t } from "../../../../i18n";
import { DecisionDialog } from "../../../../shared/DecisionDialog";
import { Button } from "../../../../shared/ui-controls";

/** «Удалить подключение?» — данные в самом сервисе не меняются. */
export function DeleteServiceDialog({ service, onClose, onConfirm }: { service: string; onClose: () => void; onConfirm: () => Promise<void> }) {
  const [busy, setBusy] = useState(false);
  return (
    <DecisionDialog open tone="danger" icon="errorCircle" width={460} centered onClose={onClose}
      title={t("services.delete_title")}
      description={t("services.delete_text", { service })}
      actions={(
        <>
          <Button variant="secondary" onClick={onClose}>{t("services.cancel")}</Button>
          <Button variant="danger-outline" disabled={busy} onClick={() => { setBusy(true); void onConfirm().finally(() => setBusy(false)); }}>
            {t("services.delete")}
          </Button>
        </>
      )} />
  );
}

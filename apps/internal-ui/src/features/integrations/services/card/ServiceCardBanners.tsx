import { t } from "../../../../i18n";
import { Icon } from "../../../../shared/icons";
import { Button } from "../../../../shared/ui-controls";
import { ServiceAlert } from "../connect/ServiceAlert";
import { checkFailureMessage } from "../model";
import type { ServiceConnection } from "../types";

/** «{Сервис} подключён» после подключения и «Нужно восстановить доступ» при потере доступа. */
export function ServiceCardBanners({ connection, service, justConnected, onHide, onRestore }: {
  connection: ServiceConnection;
  service: string;
  justConnected: boolean;
  onHide: () => void;
  onRestore: () => void;
}) {
  const failure = checkFailureMessage(connection);
  return (
    <>
      {justConnected && connection.status !== "lost" && (
        <ServiceAlert tone="success" title={t("services.connected_title", { service })} text={t("services.connected_text")}
          action={<button className="service-alert-close" type="button" title={t("services.hide")} aria-label={t("services.hide")} onClick={onHide}><Icon name="close" size={14} /></button>} />
      )}
      {connection.status === "lost" && (
        <ServiceAlert tone="error" title={failure?.title ?? t("services.lost_title")} text={failure?.text ?? t("services.lost_text")}
          action={<Button variant="primary" onClick={onRestore}>{t("services.restore")}</Button>} />
      )}
    </>
  );
}

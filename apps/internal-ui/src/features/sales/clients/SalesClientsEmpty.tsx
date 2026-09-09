import { Icon } from "../../../shared/icons";
import { t } from "../../../i18n";

// Пустой список (кадр S1, §5.2): что это, зачем и что нажать.
export function SalesClientsEmpty({ onOpenIntegrations }: { onOpenIntegrations: () => void }) {
  return (
    <div className="sales-clients-blank">
      <span><Icon name="user" size={22} /></span>
      <div>
        <strong>{t("sales.contacts_appear_once_customers_write")}</strong>
        <p>{t("sales.everyone_who_writes_through_telegram")}</p>
      </div>
      <button type="button" onClick={onOpenIntegrations}>{t("sales.set_up_connections")}</button>
    </div>
  );
}

import { Icon } from "../../../shared/icons";
import { t } from "../../../i18n";
import { ChannelNavigationMenu, type ChannelRoute } from "../../../shared/ChannelNavigationMenu";

// Пустой список (кадр S1, §5.2): что это, зачем и что нажать.
export function SalesClientsEmpty({ openChannels }: { openChannels: (route: ChannelRoute) => void }) {
  return (
    <div className="sales-clients-blank">
      <span><Icon name="user" size={22} /></span>
      <div>
        <strong>{t("sales.contacts_appear_once_customers_write")}</strong>
        <p>{t("sales.everyone_who_writes_through_telegram")}</p>
      </div>
      <ChannelNavigationMenu onNavigate={openChannels} label={t("sales.set_up_connections")} />
    </div>
  );
}

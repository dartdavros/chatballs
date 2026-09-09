import { Icon } from "../../../shared/icons";
import { t } from "../../../i18n";

// Шапка списка (кадр K1): «Контакты» и счётчик; при фильтре — «6 из 128».
export function SalesClientsHeader({ shownCount, totalCount, filtered, onExport }: { shownCount: number; totalCount: number; filtered: boolean; onExport: () => void }) {
  return (
    <div className="sales-clients-header">
      <div>
        <h2>{t("common.contacts")}</h2>
        <span>{filtered ? t("common.n_of_m", { selected: shownCount, total: totalCount }) : totalCount}</span>
      </div>
      <button className="sales-clients-export" type="button" disabled={shownCount === 0} onClick={onExport}>
        <Icon name="download" size={15} strokeWidth={2} />{t("sales.export_csv")}</button>
    </div>
  );
}

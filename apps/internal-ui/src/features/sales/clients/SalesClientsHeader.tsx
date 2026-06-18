import { Icon } from "../../../shared/icons";

export function SalesClientsHeader({ shownCount }: { shownCount: number }) {
  return (
    <div className="sales-clients-header">
      <div>
        <h1>Клиенты</h1>
        <p>Контакты отдела продаж · показано <b>{shownCount}</b> из 248</p>
      </div>
      <div className="sales-clients-header-actions">
        <button type="button"><Icon name="columns" size={15} />Столбцы</button>
        <button type="button"><Icon name="download" size={15} />Экспорт</button>
      </div>
    </div>
  );
}

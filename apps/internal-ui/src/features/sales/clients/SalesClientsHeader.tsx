import { ActionButton } from "../../../shared/ui-controls";

export function SalesClientsHeader({ shownCount }: { shownCount: number }) {
  return (
    <div className="sales-clients-header">
      <div>
        <h1>Клиенты</h1>
        <p>Контакты отдела продаж · показано <b>{shownCount}</b> из 248</p>
      </div>
      <div className="sales-clients-header-actions">
        <ActionButton icon="columns">Столбцы</ActionButton>
        <ActionButton icon="download">Экспорт</ActionButton>
      </div>
    </div>
  );
}

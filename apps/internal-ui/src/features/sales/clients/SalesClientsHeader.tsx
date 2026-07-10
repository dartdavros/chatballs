import { ActionButton } from "../../../shared/ui-controls";

export function SalesClientsHeader({ shownCount, totalCount }: { shownCount: number; totalCount: number }) {
  return (
    <div className="sales-clients-header">
      <div>
        <h1>Контакты</h1>
        <p>Лиды и клиенты отдела продаж · показано <b>{shownCount}</b> из {totalCount}</p>
      </div>
      <div className="sales-clients-header-actions">
        <ActionButton icon="columns">Столбцы</ActionButton>
        <ActionButton icon="download">Экспорт</ActionButton>
      </div>
    </div>
  );
}

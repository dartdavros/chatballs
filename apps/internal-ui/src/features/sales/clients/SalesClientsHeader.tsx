import { ActionButton } from "../../../shared/ui-controls";

export function SalesClientsHeader({ shownCount, totalCount, onExport }: { shownCount: number; totalCount: number; onExport: () => void }) {
  return (
    <div className="sales-clients-header">
      <div>
        <h1>Контакты</h1>
        <p>Контакты клиентов · показано <b>{shownCount}</b> из {totalCount}</p>
      </div>
      <div className="sales-clients-header-actions">
        <ActionButton icon="download" disabled={shownCount === 0} onClick={onExport}>Экспорт</ActionButton>
      </div>
    </div>
  );
}

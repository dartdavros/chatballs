import { ActionButton, SearchInput } from "../../../shared/ui-controls";

export function SalesOrdersHeader({ query, setQuery }: { query: string; setQuery: (value: string) => void }) {
  return (
    <div className="sales-orders-header">
      <div>
        <h1>Продажи</h1>
        <p>Заказы, платежи, возвраты, подписки и исполнение · основной объект — заказ</p>
      </div>
      <div className="sales-orders-header-actions">
        <SearchInput className="sales-orders-search" value={query} onChange={setQuery} placeholder="Поиск по ID или клиенту…" />
        <ActionButton icon="download">Экспорт</ActionButton>
      </div>
    </div>
  );
}

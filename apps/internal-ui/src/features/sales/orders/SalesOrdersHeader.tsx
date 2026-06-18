import { Icon } from "../../../shared/icons";

export function SalesOrdersHeader({ query, setQuery }: { query: string; setQuery: (value: string) => void }) {
  return (
    <div className="sales-orders-header">
      <div>
        <h1>Продажи</h1>
        <p>Заказы, платежи, возвраты, подписки и исполнение · основной объект — заказ</p>
      </div>
      <div className="sales-orders-header-actions">
        <label className="sales-orders-search">
          <Icon name="search" size={15} />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Поиск по ID или клиенту…" />
        </label>
        <button type="button"><Icon name="download" size={15} />Экспорт</button>
      </div>
    </div>
  );
}

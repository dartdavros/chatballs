export function SalesOrdersPagination({ shown, total }: { shown: number; total: number }) {
  return (
    <div className="sales-orders-pagination">
      <div>Показано {shown} из {total}</div>
      <div>
        <button type="button" disabled>‹</button>
        <button className="active" type="button">1</button>
        <button type="button">2</button>
        <button type="button">›</button>
        <span />
        <b>20 / стр.</b>
      </div>
    </div>
  );
}

export function SalesClientsPagination({ shownCount }: { shownCount: number }) {
  return (
    <div className="sales-clients-pagination">
      <div>Показано {shownCount} из 248</div>
      <div>
        <button type="button" disabled>‹</button>
        <button className="active" type="button">1</button>
        <button type="button">2</button>
        <button type="button">3</button>
        <span>…</span>
        <button type="button">25</button>
        <button type="button">›</button>
        <i />
        <em>10 / стр.</em>
      </div>
    </div>
  );
}

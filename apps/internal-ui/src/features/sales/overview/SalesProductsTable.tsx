import type { SalesOverviewVm } from "./model";

export function SalesProductsTable({ products }: { products: SalesOverviewVm["products"] }) {
  return (
    <section className="sales-table-card">
      <div className="sales-card-head">
        <h3>Продукты</h3>
        <a href="#" onClick={(event) => event.preventDefault()}>Все продукты</a>
      </div>
      <table>
        <thead>
          <tr>
            <th>ПРОДУКТ</th>
            <th>СТАТУС</th>
            <th>ПРОДАЖИ</th>
            <th>ВЫРУЧКА</th>
            <th>КОНВ.</th>
            <th>ДИАЛОГИ</th>
          </tr>
        </thead>
        <tbody>
          {products.map((product) => (
            <tr key={product.name}>
              <td><a href="#" onClick={(event) => event.preventDefault()}>{product.name}</a></td>
              <td><span className="sales-active-status"><i />{product.status}</span></td>
              <td>{product.sales}</td>
              <td>{product.rev}</td>
              <td>{product.conv}</td>
              <td>{product.dlg}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

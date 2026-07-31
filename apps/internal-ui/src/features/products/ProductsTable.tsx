import type { Product } from "../../types";
import { ProductRow } from "./ProductRow";
import type { ProductPeriod } from "./types";

export function ProductsTable({ products, period, periodLabel, menuId, setMenuId, deactivate, openProduct }: { products: Product[]; period: ProductPeriod; periodLabel: string; menuId: number | null; setMenuId: (id: number | null) => void; deactivate: (product: Product) => void; openProduct: (product: Product) => void }) {
  return (
    <div className="table-card products-card">
      <div className="product-table-scroll">
        <table className="baseline-table products-table">
          <thead><tr><th>ПРОДУКТ</th><th>СТАТУС</th><th>OFFER И ЦЕНЫ</th><th>КАНАЛЫ</th><th className="numeric">ПРОДАЖИ · {periodLabel.toUpperCase()}</th><th /></tr></thead>
          <tbody>{products.map((product) => <ProductRow product={product} period={period} menuId={menuId} setMenuId={setMenuId} deactivate={deactivate} openProduct={openProduct} key={product.id} />)}</tbody>
        </table>
      </div>
      <div className="products-footer">
        <span>{products.length} продукта</span>
        <span>Активная цена не редактируется задним числом — создаётся новая версия</span>
      </div>
    </div>
  );
}

import type { Product } from "../../../types";
import { formatProductDate, productKind } from "./model";

export function ProductOverviewTab({ product }: { product: Product }) {
  return (
    <div className="product-overview-grid">
      <div className="product-overview-main">
        <section className="product-detail-card"><h3>Описание для продаж</h3><p>{product.salesDescription || "—"}</p></section>
        <section className="product-detail-card"><h3>Ключевые тезисы для AI</h3><p className="product-detail-empty">—</p></section>
      </div>
      <aside className="product-overview-side">
        <section className="product-detail-card product-parameters">
          <h3>Параметры</h3>
          <div><span>Тип</span><strong>{productKind(product)}</strong></div>
          <div><span>Отдел</span><strong>{product.departments.map((department) => department.name).join(", ") || "—"}</strong></div>
          <div><span>Sales-agent</span><strong>—</strong></div>
          <div><span>Создан</span><strong>{formatProductDate(product.createdAt)}</strong></div>
        </section>
        <section className="product-detail-card"><h3>Sales-agent</h3><p className="product-detail-empty">—</p></section>
      </aside>
    </div>
  );
}

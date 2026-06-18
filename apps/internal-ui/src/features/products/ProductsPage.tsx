import { useState } from "react";

import { api } from "../../api/client";
import type { Product } from "../../types";
import { ProductsHeaderActions } from "./ProductsHeaderActions";
import { ProductsTable } from "./ProductsTable";
import type { ProductPeriod } from "./types";
import { PageHeader } from "../../shared/ui";

export function ProductsPage({ products, reload }: { products: Product[]; reload: () => void }) {
  const [period, setPeriod] = useState<ProductPeriod>("d30");
  const [menuId, setMenuId] = useState<number | null>(null);
  const periodLabel = { today: "Сегодня", d7: "7 дней", d30: "30 дней" }[period];
  async function deactivate(product: Product) {
    if (product.status === "DISABLED") return;
    await api(`/api/v1/company/products/${product.id}/deactivate/`, { method: "POST" });
    setMenuId(null);
    reload();
  }
  return (
    <>
      {menuId !== null && <button className="menu-scrim" aria-label="Закрыть меню" onClick={() => setMenuId(null)} />}
      <PageHeader
        title="Продукты"
        text={`${products.filter((item) => item.status === "ACTIVE").length} активных продукта · цены и Offer управляются в карточке продукта`}
        action={(
          <div className="products-header-actions">
            <ProductsHeaderActions period={period} setPeriod={(nextPeriod) => { setPeriod(nextPeriod); setMenuId(null); }} />
          </div>
        )}
      />
      <ProductsTable products={products} period={period} periodLabel={periodLabel} menuId={menuId} setMenuId={setMenuId} deactivate={deactivate} />
    </>
  );
}

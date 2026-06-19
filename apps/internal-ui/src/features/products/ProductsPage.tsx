import { useState } from "react";

import { api } from "../../api/client";
import type { Department, Product } from "../../types";
import { ProductFormModal } from "./ProductFormModal";
import { ProductsHeaderActions } from "./ProductsHeaderActions";
import { ProductsTable } from "./ProductsTable";
import type { ProductPeriod } from "./types";
import { PageHeader } from "../../shared/ui";

export function ProductsPage({ departments, products, reload, openProduct }: { departments: Department[]; products: Product[]; reload: () => void; openProduct: (product: Product) => void }) {
  const [period, setPeriod] = useState<ProductPeriod>("d30");
  const [menuId, setMenuId] = useState<number | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const periodLabel = { today: "Сегодня", d7: "7 дней", d30: "30 дней" }[period];
  async function deactivate(product: Product) {
    if (product.status === "DISABLED") return;
    await api(`/api/v1/company/products/${product.id}/deactivate/`, { method: "POST" });
    setMenuId(null);
    reload();
  }
  return (
    <>
      <PageHeader
        title="Продукты"
        text={`${products.filter((item) => item.status === "ACTIVE").length} активных продукта · цены и Offer управляются в карточке продукта`}
        action={(
          <div className="products-header-actions">
            <ProductsHeaderActions period={period} setPeriod={(nextPeriod) => { setPeriod(nextPeriod); setMenuId(null); }} onCreate={() => setFormOpen(true)} />
          </div>
        )}
      />
      <ProductsTable products={products} period={period} periodLabel={periodLabel} menuId={menuId} setMenuId={setMenuId} deactivate={deactivate} openProduct={openProduct} />
      <ProductFormModal departments={departments} open={formOpen} onClose={() => setFormOpen(false)} onSaved={reload} />
    </>
  );
}

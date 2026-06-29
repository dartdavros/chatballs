import { useState } from "react";

import { UnderlineTabs } from "../../../shared/ui-controls";
import type { Department, Product } from "../../../types";
import { ProductFormModal } from "../ProductFormModal";
import { ProductDetailHeader } from "./ProductDetailHeader";
import { ProductEmptyTab } from "./ProductEmptyTab";
import { ProductOffersTab } from "./ProductOffersTab";
import { ProductOverviewTab } from "./ProductOverviewTab";
import { productTabs, type ProductTab } from "./model";

export function ProductDetailPage({ product, departments, reload, openAgentCreate, openAgent }: { product: Product; departments: Department[]; reload: () => void; openAgentCreate: (productCode: string | null) => void; openAgent: (agentId: number) => void }) {
  const [tab, setTab] = useState<ProductTab>("overview");
  const [editing, setEditing] = useState(false);
  return (
    <>
      <ProductDetailHeader product={product} onEdit={() => setEditing(true)} />
      <UnderlineTabs className="product-detail-tabs" items={productTabs} value={tab} onChange={setTab} />
      {tab === "overview" && <ProductOverviewTab product={product} openAgentCreate={openAgentCreate} openAgent={openAgent} />}
      {tab === "offers" && <ProductOffersTab product={product} reload={reload} />}
      {tab === "channels" && <ProductEmptyTab title="Каналы продаж" subtitle="Через какие каналы продукт доступен клиентам" />}
      {tab === "fulfillment" && <ProductEmptyTab title="Способ исполнения" />}
      <ProductFormModal departments={departments} open={editing} product={product} onClose={() => setEditing(false)} onSaved={reload} />
    </>
  );
}

import { useEffect, useState } from "react";

import { api } from "../../../../api/client";
import { Icon } from "../../../../shared/icons";
import { ContextSection } from "../../../conversations/ContextSection";
import type { ApiConversation } from "../../../conversations/model";
import type { Product, ProductOffer } from "../../../../types";

const PERIOD: Record<string, string> = { ONE_TIME: "разово", MONTH: "/ мес", YEAR: "/ год" };

function priceLabel(offer: ProductOffer): string {
  const price = offer.prices.find((p) => p.isActive) ?? offer.prices[0];
  if (!price) return "—";
  const amount = (price.amountMinor / 100).toLocaleString("ru-RU");
  return `₽${amount} ${PERIOD[price.billingPeriod] ?? ""}`.trim();
}

export function ProductContext({ detail }: { detail: ApiConversation | null }) {
  const productRef = detail?.channel.product ?? null;
  const [product, setProduct] = useState<Product | null>(null);

  useEffect(() => {
    if (!productRef) {
      setProduct(null);
      return;
    }
    api<{ items: Product[] }>("/api/v1/company/products/")
      .then((r) => setProduct(r.items.find((p) => p.code === productRef.code) ?? null))
      .catch(() => setProduct(null));
  }, [productRef?.code]);

  if (!productRef) {
    return (
      <div className="sales-product-context">
        <div className="sales-product-head"><span><Icon name="box" size={20} /></span><div><strong>Без продукта</strong><small>Канал главного сайта</small></div></div>
      </div>
    );
  }

  const offers = product?.offers ?? [];
  return (
    <div className="sales-product-context">
      <div className="sales-product-head"><span><Icon name="box" size={20} /></span><div><strong>{productRef.name}</strong><small>{offers.length} предложений</small></div></div>
      <ContextSection title="ПОДХОДЯЩИЕ OFFER">
        {offers.length === 0 && <p className="sales-context-muted">Предложения не настроены</p>}
        {offers.map((offer) => (
          <div className={`sales-offer ${offer.aiOfferable ? "active" : ""}`} key={offer.id}>
            <div><strong>{offer.name}</strong>{offer.aiOfferable && <em>AI может предлагать</em>}</div>
            <p><b>{priceLabel(offer)}</b></p>
            {offer.description && <small>{offer.description}</small>}
          </div>
        ))}
      </ContextSection>
    </div>
  );
}

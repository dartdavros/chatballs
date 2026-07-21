import { Icon } from "../../../shared/icons";
import { EmptyState } from "../../../shared/ui";
import type { Product } from "../../../types";
import { fulfillmentOptions, paymentOptions } from "./offerApi";

const fulfillmentLabel = Object.fromEntries(fulfillmentOptions);
const paymentLabel = Object.fromEntries(paymentOptions);

export function ProductAccessTab({ product }: { product: Product }) {
  const offers = product.offers.filter((offer) => offer.isActive);

  return (
    <div className="product-access-tab">
      <div className="ai-notice">
        <Icon name="warning" size={17} />
        <span>Каталог (как продаётся и фискальные данные) живёт в Хабе. Само исполнение — выдача доступа, метрики, операции — на стороне бэкенда продукта.</span>
      </div>

      <section className="product-detail-card">
        <h3>Продукт</h3>
        <div className="product-access-grid">
          <div><span>Сайт</span>{product.siteUrl ? <a href={product.siteUrl} target="_blank" rel="noreferrer">{product.siteUrl}</a> : <b className="product-empty-value">—</b>}</div>
          <div><span>Активных предложений</span><b>{offers.length}</b></div>
        </div>
      </section>

      {offers.length === 0 ? (
        <EmptyState title="Нет активных предложений" />
      ) : (
        offers.map((offer) => {
          const schema = Object.entries(offer.accessSchema ?? {});
          return (
            <section className="product-detail-card" key={offer.id}>
              <div className="product-access-offer-head">
                <h3>{offer.name}</h3>
                <code>{offer.code}</code>
              </div>
              <div className="product-access-grid">
                <div><span>Способ исполнения</span><b>{fulfillmentLabel[offer.fulfillmentType] ?? offer.fulfillmentType}</b></div>
                <div><span>Тип оплаты</span><b>{paymentLabel[offer.paymentType] ?? offer.paymentType}</b></div>
                <div><span>Фискальное наименование</span><b>{offer.fiscalName || <span className="product-empty-value">—</span>}</b></div>
              </div>
              {schema.length > 0 && (
                <div className="product-access-schema">
                  <span>Схема доступа</span>
                  {schema.map(([key, value]) => <div key={key}><code>{key}</code><b>{String(value)}</b></div>)}
                </div>
              )}
            </section>
          );
        })
      )}
    </div>
  );
}

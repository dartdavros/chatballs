import { Icon } from "../../../shared/icons";
import { Button } from "../../../shared/ui-controls";
import { productAccent } from "../../../shared/utils";
import type { Product } from "../../../types";
import { productKind } from "./model";

export function ProductDetailHeader({ product, onEdit }: { product: Product; onEdit: () => void }) {
  const accent = productAccent(product.code);
  const kind = productKind(product);
  return (
    <section className="product-detail-header">
      <div className="product-detail-heading">
        <span className="product-detail-icon" style={{ background: accent.bg, color: accent.color }}><Icon name="box" size={26} /></span>
        <div className="product-detail-title">
          <div><h1>{product.name}</h1><span className={`product-detail-status ${product.status.toLowerCase()}`}><i />{product.status === "ACTIVE" ? "Активен" : "Неактивен"}</span>{kind !== "—" && <b style={{ background: accent.bg, color: accent.color }}>{kind}</b>}</div>
          <p>{product.summary || "—"}</p>
        </div>
        <Button variant="secondary" icon="edit" onClick={onEdit}>Редактировать</Button>
      </div>
      <div className="product-detail-stats">
        <div><span>Продажи · 30 дней</span><strong>0</strong></div>
        <div><span>Выручка · 30 дней</span><strong className="positive">₽0</strong></div>
        <div><span>Активные Offer</span><strong>{product.offers.filter((offer) => offer.isActive).length}</strong></div>
        <div><span>Конверсия диалогов</span><strong>0%</strong></div>
      </div>
    </section>
  );
}

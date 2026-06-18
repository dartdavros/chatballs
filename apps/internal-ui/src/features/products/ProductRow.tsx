import type { Product } from "../../types";
import { Icon } from "../../shared/icons";
import { StatusPill } from "../../shared/ui";
import { productAccent } from "../../shared/utils";
import { productDetails } from "./model";
import type { ProductPeriod } from "./types";

export function ProductRow({ product, period, menuId, setMenuId, deactivate }: { product: Product; period: ProductPeriod; menuId: number | null; setMenuId: (id: number | null) => void; deactivate: (product: Product) => void }) {
  const accent = productAccent(product.code);
  const details = productDetails(product);
  const sales = details.sales[period];
  const menuOpen = menuId === product.id;
  return (
    <tr>
      <td><div className="product-cell"><span className="product-icon" style={{ background: accent.bg, color: accent.color }}><Icon name="box" size={21} /></span><span><strong>{product.name}</strong><small>{details.sub}</small></span></div></td>
      <td><StatusPill status={product.status === "ACTIVE" ? "active" : "disabled"} /></td>
      <td>
        <div className="offer-list">
          {details.offers.map((offer) => <div key={`${product.id}-${offer.name}`}><span>{offer.name} <em>· {offer.type}</em></span><strong>{offer.price}</strong></div>)}
          {details.note && <p><Icon name="percent" size={11} />{details.note}</p>}
        </div>
      </td>
      <td><div className="agent-state"><span><i />AI-агент</span><small>{details.agentRelease}</small></div></td>
      <td><div className="channel-tags">{details.channels.map((channel) => <span style={{ background: channel.bg, color: channel.color }} key={channel.label}><i style={{ background: channel.color }} />{channel.label}</span>)}</div></td>
      <td><div className="fulfillment-state"><span><i />Подключён</span><small>{details.fulfillment}</small></div></td>
      <td className="numeric"><div className="product-sales"><strong>{sales.sum}</strong><small>{sales.n} продаж</small></div></td>
      <td className="row-actions">
        <button className="row-menu-button" aria-label="Действия продукта" onClick={() => setMenuId(menuOpen ? null : product.id)}><Icon name="more" /></button>
        {menuOpen && (
          <div className="row-menu product-row-menu">
            <a href="#" onClick={(event) => event.preventDefault()}><Icon name="external" size={15} />Открыть продукт</a>
            <a href="#" onClick={(event) => event.preventDefault()}><Icon name="plus" size={15} />Добавить Offer</a>
            <span />
            <button className="warning" onClick={() => deactivate(product)} disabled={product.status === "DISABLED"}><Icon name="pause" size={15} />Деактивировать</button>
          </div>
        )}
      </td>
    </tr>
  );
}

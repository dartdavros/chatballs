import { Dropdown } from "antd";

import type { Product } from "../../types";
import { Icon } from "../../shared/icons";
import { StatusPill } from "../../shared/ui";
import { productAccent } from "../../shared/utils";
import { productDetails } from "./model";
import type { ProductPeriod } from "./types";

export function ProductRow({ product, period, menuId, setMenuId, deactivate, openProduct }: { product: Product; period: ProductPeriod; menuId: number | null; setMenuId: (id: number | null) => void; deactivate: (product: Product) => void; openProduct: (product: Product) => void }) {
  const accent = productAccent(product.code);
  const details = productDetails(product);
  const sales = details.sales[period];
  const menuOpen = menuId === product.id;
  const menuItems = [
    { key: "open", label: <button type="button" onClick={() => openProduct(product)}><Icon name="external" size={15} />Открыть продукт</button> },
    { type: "divider" as const },
    { key: "status", disabled: product.status === "DISABLED", label: <button className="warning" type="button" onClick={() => deactivate(product)}><Icon name="pause" size={15} />Деактивировать</button> },
  ];
  return (
    <tr>
      <td><div className="product-cell"><span className="product-icon" style={{ background: accent.bg, color: accent.color }}><Icon name="box" size={21} /></span><span><button className="link is-strong" type="button" onClick={() => openProduct(product)}>{product.name}</button><small>{details.sub}</small></span></div></td>
      <td><StatusPill status={product.status === "ACTIVE" ? "active" : "disabled"} /></td>
      <td>
        <div className="offer-list">
          {details.offers.length ? details.offers.map((offer) => <div key={`${product.id}-${offer.name}`}><span>{offer.name} <em>· {offer.type}</em></span><strong>{offer.price}</strong></div>) : <span className="product-empty-value">—</span>}
        </div>
      </td>
      <td><span className="product-empty-value">—</span></td>
      <td><span className="product-empty-value">—</span></td>
      <td><span className="product-empty-value">—</span></td>
      <td className="numeric"><div className="product-sales"><strong>{sales.sum}</strong><small>{sales.n} продаж</small></div></td>
      <td className="row-actions">
        <Dropdown menu={{ items: menuItems }} open={menuOpen} onOpenChange={(open) => setMenuId(open ? product.id : null)} trigger={["click"]} overlayClassName="app-dropdown">
          <button className="row-menu-button" type="button" aria-label="Действия продукта"><Icon name="more" /></button>
        </Dropdown>
      </td>
    </tr>
  );
}

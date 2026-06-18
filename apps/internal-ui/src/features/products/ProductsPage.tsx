import { useState } from "react";

import { api } from "../../api/client";
import type { Product } from "../../types";
import { Icon } from "../../shared/icons";
import { productAccent } from "../../shared/utils";
import { PageHeader, Segmented, StatusPill } from "../../shared/ui";

type ProductPeriod = "today" | "d7" | "d30";

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
            <Segmented value={period} setValue={(nextPeriod) => { setPeriod(nextPeriod); setMenuId(null); }} items={[["today", "Сегодня"], ["d7", "7 дней"], ["d30", "30 дней"]]} />
            <button className="primary-button" type="button"><Icon name="plus" size={16} />Создать продукт</button>
          </div>
        )}
      />
      <div className="table-card products-card">
        <div className="product-table-scroll">
          <table className="baseline-table products-table">
            <thead><tr><th>ПРОДУКТ</th><th>СТАТУС</th><th>OFFER И ЦЕНЫ</th><th>SALES-AGENT</th><th>КАНАЛЫ</th><th>FULFILLMENT</th><th className="numeric">ПРОДАЖИ · {periodLabel.toUpperCase()}</th><th /></tr></thead>
            <tbody>{products.map((product) => <ProductRow product={product} period={period} menuId={menuId} setMenuId={setMenuId} deactivate={deactivate} key={product.id} />)}</tbody>
          </table>
        </div>
        <div className="products-footer">
          <span>{products.length} продукта</span>
          <span>Активная цена не редактируется задним числом — создаётся новая версия</span>
        </div>
      </div>
    </>
  );
}

function ProductRow({ product, period, menuId, setMenuId, deactivate }: { product: Product; period: ProductPeriod; menuId: number | null; setMenuId: (id: number | null) => void; deactivate: (product: Product) => void }) {
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

function productDetails(product: Product) {
  const base = {
    sub: product.siteUrl || product.code,
    offers: [{ name: "—", type: "—", price: "—" }],
    note: "",
    agentRelease: "release —",
    channels: [] as Array<{ label: string; color: string; bg: string }>,
    fulfillment: "—",
    sales: {
      today: { n: 0, sum: "₽0" },
      d7: { n: 0, sum: "₽0" },
      d30: { n: 0, sum: "₽0" },
    },
  };
  const channels = {
    max: { label: "MAX", color: "#6b5be0", bg: "#f2f0ff" },
    tg: { label: "TG", color: "#2f8fd0", bg: "#eaf6fd" },
    web: { label: "Web", color: "#0f9b8e", bg: "#e8f7f4" },
  };
  if (product.code === "firepage") {
    return {
      sub: "Нишевые сайты · коробка",
      offers: [
        { name: "Коробка", type: "разовая", price: "₽4 900" },
        { name: "Годовая поддержка", type: "продление", price: "₽1 470 / год" },
      ],
      note: "Поддержка — 30% от цены коробки",
      agentRelease: "release v4 · published",
      channels: [channels.max, channels.tg, channels.web],
      fulfillment: "Сборка и выдача сайта",
      sales: {
        today: { n: 2, sum: "₽9 800" },
        d7: { n: 14, sum: "₽71 540" },
        d30: { n: 56, sum: "₽288 100" },
      },
    };
  }
  if (product.code === "foxray") {
    return {
      sub: "SaaS · подписка",
      offers: [
        { name: "Pro", type: "подписка", price: "₽4 900 / мес" },
        { name: "Max", type: "подписка", price: "₽9 900 / мес" },
      ],
      note: "Скидка 20% при оплате за год",
      agentRelease: "release v3 · published",
      channels: [channels.max, channels.tg, channels.web],
      fulfillment: "Выдача доступа",
      sales: {
        today: { n: 3, sum: "₽16 400" },
        d7: { n: 19, sum: "₽104 200" },
        d30: { n: 82, sum: "₽548 700" },
      },
    };
  }
  return base;
}

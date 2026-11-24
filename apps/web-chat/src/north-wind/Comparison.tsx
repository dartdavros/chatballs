import { t } from "./language";
import { useEffect, useRef, type ReactNode } from 'react';
import { money, type Product, type ProductId } from './products';
import { Icon } from './Icons';
import { trapModalTab } from './modalFocus';

export function StoreDialog({ title, onClose, children, className = '' }: { title: string; onClose: () => void; children: ReactNode; className?: string }) {
  const ref = useRef<HTMLElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  useEffect(() => {
    const oldOverflow = document.body.style.overflow;
    const root = ref.current?.getRootNode() as Document | ShadowRoot;
    const previous = root?.activeElement as HTMLElement | null;
    document.body.style.overflow = 'hidden';
    closeRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (ref.current?.closest('[inert]')) return;
      if (event.key === 'Escape') { event.preventDefault(); onCloseRef.current(); }
      trapModalTab(event, ref.current);
    };
    window.addEventListener('keydown', onKey);
    return () => { document.body.style.overflow = oldOverflow; window.removeEventListener('keydown', onKey); if (previous?.isConnected) previous.focus(); };
  }, []);
  return <div className="store-dialog-backdrop" onClick={event => { if (event.target === event.currentTarget) onClose(); }}>
    <section ref={ref} className={`store-dialog ${className}`} role="dialog" aria-modal="true" aria-label={title}>
      <header className="store-dialog-heading"><h2>{title}</h2><button ref={closeRef} type="button" onClick={onClose} aria-label={t("close_dialog")}><Icon name="X" size={22} /></button></header>
      {children}
    </section>
  </div>;
}

export function Comparison({ selected, products, onToggle, onBuy, onClose }: { selected: ProductId[]; products: Product[]; onToggle: (id: ProductId) => void; onBuy: (id: ProductId) => void; onClose: () => void }) {
  const items = products.filter(item => selected.includes(item.id));
  const rows: { label: string; value: (item: Product) => string }[] = [
    { label: t("discounted_price"), value: item => money(item.price) },
    { label: t("material"), value: item => item.material },
    { label: t("lining"), value: item => item.lining },
    { label: t("membrane"), value: item => item.membrane },
    { label: t("breathability"), value: item => item.breathability },
    { label: t("colour"), value: item => item.colorName },
    { label: t("sizes"), value: item => item.sizes.join(', ') },
  ];
  return <StoreDialog title={`${t("compare_dialog")}${items.length ? ` · ${items.length}` : ''}`} onClose={onClose} className="store-comparison-dialog">
    <div className="store-dialog-content">
      {items.length > 0 && <div className="store-comparison-scroll"><table className="store-comparison-table"><thead><tr><th scope="col">{t("specifications")}</th>{items.map(item => <th scope="col" key={item.id}><button type="button" className="store-comparison-remove" onClick={() => onToggle(item.id)} aria-label={t("compare_remove", {name: item.name})}><Icon name="X" size={16} /></button><img src={item.photo} alt={item.name} /><strong>{item.name}</strong><span>{t("men_suit")}</span></th>)}</tr></thead><tbody>{rows.map(row => <tr key={row.label}><th scope="row">{row.label}</th>{items.map(item => <td key={item.id}>{row.value(item)}</td>)}</tr>)}<tr><th /><>{items.map(item => <td key={item.id}><button type="button" className="store-buy-button" onClick={() => { onBuy(item.id); onClose(); }}>{t("buy")}</button></td>)}</></tr></tbody></table></div>}
      {items.length < 3 && <div className="store-comparison-add"><h3>{items.length ? t("compare_add") : t("compare_pick")}</h3><p>{t("compare_up_to")}</p><div>{products.filter(item => !selected.includes(item.id)).map(item => <button type="button" key={item.id} onClick={() => onToggle(item.id)}><img src={item.photo} alt="" /><span>{item.name}<small>{money(item.price)}</small></span><Icon name="Compare" size={18} /></button>)}</div></div>}
    </div>
  </StoreDialog>;
}

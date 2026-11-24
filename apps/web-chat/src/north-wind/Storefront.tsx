import { t, tn } from "./language";
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { money, storeLabel, type ProductId } from './products';
import type { ShopDisplay, ShopOptions } from './model';
import { Icon } from './Icons';
import { Comparison, StoreDialog } from './Comparison';
import { defaultPickupBudget, PickupFilters } from './PickupFilters';
import { StoreCatalogGrid } from './StoreCatalogGrid';
import { StoreHeader } from './StoreHeader';
import './storefront.css';

type GalleryView = typeof galleryViews[number];
const galleryViews = ['full', 'jacket', 'pants'] as const;
const sizeChart = [
  { size: 'M', russian: '48–50', chest: '96–100', waist: '84–88', hips: '100–104' },
  { size: 'L', russian: '50–52', chest: '100–104', waist: '88–92', hips: '104–108' },
  { size: 'XL', russian: '52–54', chest: '104–108', waist: '92–96', hips: '108–112' },
] as const;

export function Storefront({ state, options, onOptions, onProduct, onCart, onBuy, checkout, navigationKey, catalogRequest, onPickupSelection }: {
  state: ShopDisplay; options: ShopOptions;
  onOptions: (patch: Partial<ShopOptions>) => void;
  onProduct: (id: ProductId) => void;
  onCart: () => void;
  onBuy: (id: ProductId) => void;
  checkout?: ReactNode;

  navigationKey?: number;
  catalogRequest: number;
  onPickupSelection?: (budget: number) => void;

}) {
  const { product, products } = state;
  const gallery = galleryViews.map(id => ({ id, label: t(`gallery_${id}`) }));
  const [mode, setMode] = useState<'product' | 'catalog' | 'favorites'>('product');
  const [query, setQuery] = useState('');
  const [budget, setBudget] = useState(defaultPickupBudget);
  const [appliedBudget, setAppliedBudget] = useState<number | null>(null);
  const [favorites, setFavorites] = useState<ProductId[]>([]);
  const [compared, setCompared] = useState<ProductId[]>([]);
  const [comparisonOpen, setComparisonOpen] = useState(false);
  const [sizeOpen, setSizeOpen] = useState(false);
  const [zoomOpen, setZoomOpen] = useState(false);
  const [view, setView] = useState<GalleryView>('full');
  const [tab, setTab] = useState<'description' | 'details' | 'delivery'>('description');
  const [notice, setNotice] = useState('');
  const catalogRef = useRef<HTMLElement>(null);
  const informationRef = useRef<HTMLElement>(null);
  useEffect(() => {
    setMode('product'); setQuery(''); setComparisonOpen(false); setSizeOpen(false); setZoomOpen(false); setNotice('');
  }, [navigationKey]);
  useEffect(() => {
    if (catalogRequest) { setMode("catalog"); setQuery(""); }
  }, [catalogRequest]);
  const isFavorite = favorites.includes(product.id);
  const isCompared = compared.includes(product.id);
  const inCart = state.cart?.productId === product.id;
  const showingCatalog = mode !== 'product';
  const catalog = products.filter(item => (mode !== 'favorites' || favorites.includes(item.id))
    && (mode !== 'catalog' || appliedBudget === null || item.basePrice <= appliedBudget)
    && `${item.name} ${item.colorName} ${item.material} ${t("search_terms")}`.toLowerCase().includes(query.trim().toLowerCase()));
  const toggleFavorite = (id: ProductId) => {
    setFavorites(previous => previous.includes(id) ? previous.filter(value => value !== id) : [...previous, id]);
  };
  const toggleCompare = (id: ProductId) => {
    if (compared.includes(id)) { setCompared(previous => previous.filter(value => value !== id)); setNotice(''); return; }
    if (compared.length >= 3) { setNotice(t("compare_limit")); setComparisonOpen(true); return; }
    setCompared(previous => [...previous, id]); setNotice('');
  };
  const showCatalog = (next: 'catalog' | 'favorites' = 'catalog') => {
    setMode(next); setQuery('');
    requestAnimationFrame(() => catalogRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
  };
  const buy = (id = product.id) => { setMode('product'); setQuery(''); onBuy(id); };
  const openCart = () => { setMode('product'); setQuery(''); onCart(); };
  const showInformation = (next: typeof tab) => { setTab(next); requestAnimationFrame(() => informationRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })); };
  const catalogActions = {favorites, compared, onProduct, onBuy: buy, onFavorite: toggleFavorite, onCompare: toggleCompare};

  return <div className="storefront">
    <StoreHeader
      customer={state.customer}
      personalized={product.price < product.basePrice}
      favorites={favorites.length}
      compared={compared.length}
      cart={Boolean(state.cart)}
      showingFavorites={mode === "favorites"}
      query={query}
      onBrowse={showCatalog}
      onSearch={value => { setQuery(value); setMode("catalog"); }}
      onCompare={() => setComparisonOpen(true)}
      onCart={openCart}
    />
    <div className="shop-content">
      {showingCatalog ? <section ref={catalogRef} className="store-catalog-page">
        <div className="store-catalog-heading"><div><h2>{mode === 'favorites' ? t("favorites") : query.trim() ? t("search_results", {query: query.trim()}) : t("ski_suits")}</h2><span>{tn("product_count", catalog.length)}</span></div><button type="button" className="store-text-button" onClick={() => { setMode('product'); setQuery(''); }}><Icon name="ArrowLeft" size={15} />{checkout ? t("back_checkout") : t("back_product")}</button></div>
        {mode === 'catalog' && onPickupSelection && <PickupFilters size={options.size} store={options.store} budget={budget}
          onSize={size => onOptions({size})} onStore={store => onOptions({store})} onBudget={setBudget}
          onSelection={() => { setAppliedBudget(budget); onPickupSelection(budget); }} />}
        {catalog.length ? <StoreCatalogGrid {...catalogActions} products={catalog} /> : <div className="store-empty"><Icon name={mode === 'favorites' ? 'Heart' : 'Search'} size={35} /><h3>{mode === 'favorites' ? t("favorites_empty") : t("no_results")}</h3><p>{mode === 'favorites' ? t("favorites_hint") : t("search_hint")}</p><button type="button" className="store-secondary-button" onClick={() => showCatalog()}>{t("view_suits")}</button></div>}
      </section> : checkout ? checkout : <>
        <nav className="shop-breadcrumb" aria-label={t("breadcrumb")}><button type="button" onClick={() => showCatalog()}>{t("catalog")}</button><Icon name="ChevronRight" size={11} /><button type="button" onClick={() => showCatalog()}>{t("skiing")}</button><Icon name="ChevronRight" size={11} /><button type="button" onClick={() => showCatalog()}>{t("suits")}</button><Icon name="ChevronRight" size={11} /><span>{product.name}</span></nav>
        <div className="store-product-heading"><h2>{t("men_suit_title", {name: product.name})}</h2><div><span>{t("sku_value", {sku: product.article})}</span><button type="button" className={isCompared ? 'is-active' : ''} aria-pressed={isCompared} onClick={() => toggleCompare(product.id)}><Icon name="Compare" size={15} />{isCompared ? t("already_compared") : t("compare")}</button></div></div>
        <section className="store-pdp" aria-label={t("product_panel", {name: product.name})}>
          <div className="store-gallery"><div className="store-thumbnails" role="group" aria-label={t("product_photos")}>{gallery.map(item => <button type="button" key={item.id} className={`store-thumbnail store-photo--${item.id}${view === item.id ? ' is-active' : ''}`} aria-pressed={view === item.id} aria-label={item.label} onClick={() => setView(item.id)}><img src={product.photo} alt="" /></button>)}</div><div className="store-main-photo-wrap"><button type="button" className={`store-main-photo store-photo--${view}`} onClick={() => setZoomOpen(true)} aria-label={t("zoom_view", {view: gallery.find(item => item.id === view)!.label})}><img key={product.photo} src={product.photo} alt={t("suit_photo_alt", {name: product.name})} /><span className="store-zoom-icon"><Icon name="ZoomIn" size={21} /></span></button><div className="store-photo-caption">{gallery.find(item => item.id === view)!.label}</div></div></div>
          <div className="store-buybox">
            <div className="store-product-price"><strong>{money(product.price)}</strong>{product.price < product.basePrice && <><s>{money(product.basePrice)}</s><span>−10%</span></>}</div>{product.price < product.basePrice && <p className="store-discount-note">{t("loyalty_discount_included")}</p>}
            <div className="store-color"><span>{t("colour_label")} <strong>{product.colorName.toLowerCase()}</strong></span><span className="store-color-swatch" style={{ background: product.color }} aria-label={product.colorName} /></div>
            <div className="store-size-heading"><span>{t("size")}</span><button type="button" onClick={() => setSizeOpen(true)}><Icon name="Ruler" size={14} />{t("size_chart")}</button></div>
            <div className="store-size-picker" role="group" aria-label={t("size_select")}>{product.sizes.map(size => <button type="button" key={size} className={options.size === size ? 'is-active' : ''} aria-pressed={options.size === size} onClick={() => onOptions({ size })}>{size}</button>)}</div>
            <p className="store-size-caption">{t("russian_size_value", {size: sizeChart.find(row => row.size === options.size)?.russian ?? ""})}</p>
            <button type="button" className="store-buy-button store-main-buy" onClick={() => inCart ? openCart() : buy()}>{inCart ? t("in_cart") : t("buy")}{inCart ? <Icon name="Check" size={19} /> : <Icon name="ShoppingCart" size={19} />}</button>
            <div className="store-product-actions"><button type="button" className={isFavorite ? 'is-active' : ''} aria-pressed={isFavorite} onClick={() => toggleFavorite(product.id)}><Icon name="Heart" size={18} />{isFavorite ? t("already_favorite") : t("add_favorite")}</button><button type="button" className={isCompared ? 'is-active' : ''} aria-pressed={isCompared} onClick={() => toggleCompare(product.id)}><Icon name="Compare" size={18} />{isCompared ? t("already_compared") : t("compare")}</button></div>
            {isCompared && <button type="button" className="store-comparison-link" onClick={() => setComparisonOpen(true)}>{t("compare_open", {count: compared.length})}<Icon name="ChevronRight" size={14} /></button>}
            {notice && <p className="store-inline-notice" role="status">{notice}</p>}
            <div className="store-availability"><div><Icon name="MapPin" size={19} /><span><strong>{t("kazan_pickup")}</strong><small>{t("pickup_two_stores")}</small></span><button type="button" onClick={() => showInformation('delivery')} aria-label={t("view_pickup_stores")}><Icon name="ChevronRight" size={18} /></button></div><div><Icon name="ShoppingBag" size={19} /><span><strong>{t("pay_on_pickup")}</strong><small>{t("choose_store_checkout")}</small></span></div></div>
            <dl className="store-short-facts"><div><dt>{t("membrane")}</dt><dd>{product.membrane}</dd></div><div><dt>{t("lining")}</dt><dd>{product.lining}</dd></div><div><dt>{t("set")}</dt><dd>{t("jacket_and_pants")}</dd></div></dl><button type="button" className="store-text-button store-all-specs" onClick={() => showInformation('details')}>{t("all_specs")}<Icon name="ChevronRight" size={14} /></button>
          </div>
        </section>
        <section ref={informationRef} className="store-information">
          <div className="store-tabs" role="tablist" aria-label={t("product_information")}>{([{ id: 'description', label: t("description") }, { id: 'details', label: t("specifications") }, { id: 'delivery', label: t("delivery_pickup") }] as const).map(item => <button type="button" key={item.id} id={`store-tab-${item.id}`} className={tab === item.id ? 'is-active' : ''} role="tab" aria-selected={tab === item.id} aria-controls="store-information-panel" onClick={() => setTab(item.id)}>{item.label}</button>)}</div>
          <div id="store-information-panel" className="store-information-panel" role="tabpanel" aria-labelledby={`store-tab-${tab}`}>
            {tab === 'description' && <><h3>{t("suit_photo_alt", {name: product.name})}</h3><p>{product.description}</p><p>{t("set_description", {material: product.material.toLowerCase(), lining: product.lining.toLowerCase(), membrane: product.membrane, breathability: product.breathability})}</p><button type="button" className="store-text-button" onClick={() => setTab('details')}>{t("more_specs")}<Icon name="ArrowRight" size={15} /></button></>}
            {tab === 'details' && <dl className="store-full-facts">{[[t("material"), product.material], [t("lining"), product.lining], [t("membrane"), product.membrane], [t("breathability"), product.breathability], [t("colour"), product.colorName], [t("set"), t("jacket_and_pants")], [t("sizes"), product.sizes.join(', ')], [t("sku"), product.article]].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>}
            {tab === 'delivery' && <><h3>{t("pickup_title")}</h3><p>{t("pickup_free")}</p><div className="store-pickup-locations">{state.inventory.map(row => <div key={row.store}><Icon name="MapPin" size={20} /><div><h4>{t("brand")} · {storeLabel(row.store)}</h4><p>{row.address}</p><small>{row.hours}</small><strong>{t("pickup_stock", {size: options.size, count: row.available})}</strong></div></div>)}</div></>}
          </div>
        </section>
        <section ref={catalogRef} className="store-related"><div className="store-catalog-heading"><div><h2>{t("related")}</h2></div><button type="button" className="store-text-button" onClick={() => showCatalog()}>{t("all_models")}<Icon name="ArrowRight" size={15} /></button></div>{<StoreCatalogGrid {...catalogActions} products={products.filter(item => item.id !== product.id)} />}</section>
      </>}
    </div>
    {compared.length >= 2 && !comparisonOpen && <div className="store-compare-tray"><span><Icon name="Compare" size={19} />{tn("compared_count", compared.length)}</span><button type="button" onClick={() => setComparisonOpen(true)}>{t("compare")}<Icon name="ArrowRight" size={15} /></button><button type="button" className="store-compare-clear" onClick={() => setCompared([])} aria-label={t("clear_comparison")}><Icon name="X" size={16} /></button></div>}
    {comparisonOpen && <Comparison selected={compared} products={products} onToggle={toggleCompare} onBuy={buy} onClose={() => setComparisonOpen(false)} />}
    {sizeOpen && <StoreDialog title={t("size_chart")} onClose={() => setSizeOpen(false)} className="store-size-dialog"><div className="store-dialog-content"><p>{t("size_hint")}</p><div className="store-size-table-scroll"><table className="store-size-table"><thead><tr><th>{t("size")}</th><th>{t("russian_size")}</th><th>{t("chest")}</th><th>{t("waist")}</th><th>{t("hips")}</th></tr></thead><tbody>{sizeChart.map(row => <tr key={row.size} className={options.size === row.size ? 'is-active' : ''}><td><button type="button" onClick={() => { onOptions({ size: row.size }); setSizeOpen(false); }}>{row.size}</button></td><td>{row.russian}</td><td>{row.chest}</td><td>{row.waist}</td><td>{row.hips}</td></tr>)}</tbody></table></div><p>{t("size_measure")}</p></div></StoreDialog>}
    {zoomOpen && <StoreDialog title={`${product.name} · ${gallery.find(item => item.id === view)!.label}`} onClose={() => setZoomOpen(false)} className="store-gallery-dialog"><div className={`store-gallery-expanded store-photo--${view}`}><img src={product.photo} alt={product.name} /></div><div className="store-gallery-modal-tabs">{gallery.map(item => <button type="button" key={item.id} className={view === item.id ? 'is-active' : ''} onClick={() => setView(item.id)}>{item.label}</button>)}</div></StoreDialog>}
  </div>;
}

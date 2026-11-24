import { useEffect, useState, type CSSProperties } from "react";
import { createRoot } from "react-dom/client";

import { CartDetails } from "./CartDetails";
import { FittingDetails } from "./FittingDetails";
import { ProductDetails } from "./ProductDetails";
import { Storefront } from "./Storefront";
import { ExchangeFlow } from "./exchange/ExchangeFlow";
import { ProposalForm } from "./proposal/ProposalForm";
import type { ProductId, Size } from "./model";
import { customerProfile, displayInventory, displayProduct } from "./products";
import { initializeShopLanguage, t } from "./language";
import { storefrontApi } from "./shopApi";
import { pickupLink } from "./pickupLink";
import { useNorthWindShop } from "./useNorthWindShop";
import { useShopWidgetOffset } from "./useShopWidgetOffset";
import { emitShopSiteEvent, mountShopWidget, openPreparedShopWidget } from "./widgetLauncher";
import "./page.css";
import "./product-cards.css";

const argumentsFromLink = new URLSearchParams(location.search);
const linkedProduct = pickupLink(argumentsFromLink);

function Shop({token}: {token: string}) {
  const shop = useNorthWindShop(token, linkedProduct);
  const [details, setDetails] = useState<ProductId | null>(null);
  const [detailsSize, setDetailsSize] = useState<Size>("L");
  const [entryView, setEntryView] = useState(() => argumentsFromLink.get("view"));
  const [catalogRequest, requestCatalogue] = useState(0);
  const [executorUnavailable, setExecutorUnavailable] = useState(false);
  const widgetKey = shop.data?.widgetKey;
  const preparedChat = shop.data?.preparedChat;
  const widgetWidth = useShopWidgetOffset(widgetKey);
  const loyaltyEvent = shop.data?.loyaltyEvent;
  const preparedExchange = shop.data?.customer === "andrey-after-purchase";
  const exchangeView = entryView === "exchange" && (preparedExchange || shop.data?.customer === "andrey");
  const requestedOrder = argumentsFromLink.get("order") ?? "2042";
  const exchangeOrderNumber = /^[1-9][0-9]{0,8}$/.test(requestedOrder) ? Number(requestedOrder) : 2042;

  useEffect(() => {
    if (!widgetKey || exchangeView) return;
    if (entryView === "executor") {
      let current = true;
      void storefrontApi(token)<{widgetKey: string; token: string}>("executor", {})
        .then(async session => { if (current) await openPreparedShopWidget(session); })
        .catch(() => { if (current) setExecutorUnavailable(true); });
      return () => { current = false; };
    }
    if (loyaltyEvent && !entryView) {
      void emitShopSiteEvent({widgetKey, name: loyaltyEvent, eventId: crypto.randomUUID(), data: {product: "alpine"}})
        .catch(() => { /* The storefront remains usable if the widget fails to load. */ });
    } else {
      void mountShopWidget(widgetKey, preparedChat).catch(() => { /* The storefront remains usable if the widget fails to load. */ });
    }
  }, [widgetKey, exchangeView, entryView, loyaltyEvent, preparedChat, token]);

  const {data, options, view, cart, order, quote} = shop;
  if (!data) return <main className="storefront shop-content"><p role="status">{shop.error || t("shop_loading")}</p></main>;
  const products = data.products.map(item => displayProduct(item, data.customer));
  const current = view === "checkout" && (order || cart) || options;
  const product = products.find(item => item.id === current.productId) ?? products[0];
  const available = data.products.find(item => item.id === product.id) ?? data.products[0];
  const state = {
    products, product, order, quote,
    inventory: displayInventory(available, current.size),
    customer: {...customerProfile(data.customer), balance: data.balance},
    cart: order || cart ? {...(order ?? cart!), productName: product.name} : null,
  };
  const activeProduct = products.find(item => item.id === details);

  const layout = widgetWidth ? {"--case-widget-width": `${widgetWidth}px`} as CSSProperties : undefined;
  return <main className={`north-wind-app${widgetWidth ? " case-scene--open" : ""}`} style={layout}>
    <Storefront
      state={state}
      options={options}
      onOptions={shop.updateOptions}
      onProduct={id => { setDetailsSize(options.size); setDetails(id); }}
      onBuy={shop.buy}
      onCart={shop.showCart}
      navigationKey={shop.navigationKey}
      catalogRequest={catalogRequest || (data.pickupEvent && !linkedProduct && shop.navigationKey === 0 ? 1 : 0)}
      onPickupSelection={data.pickupEvent ? budget => {
        void emitShopSiteEvent({widgetKey: data.widgetKey, name: data.pickupEvent!, eventId: crypto.randomUUID(),
          data: {category: "ski-suits", city: "kazan", size: options.size, store: options.store, budget}}).catch(() => {});
      } : undefined}
      checkout={exchangeView ? <ExchangeFlow token={token} products={products} orderNumber={exchangeOrderNumber}
        widgetKey={data.widgetKey} prepared={preparedExchange} /> : entryView === "proposal" && data.customer === "school" ? <ProposalForm
        token={token} products={products} onBack={() => { setEntryView(null); requestCatalogue(value => value + 1); }}
      /> : entryView === "fitting" ? <FittingDetails token={token} products={products} onBack={() => setEntryView(null)} /> : view === "checkout" && <CartDetails
        state={state}
        store={options.store}
        bonus={shop.bonus}
        pending={shop.pending}
        error={shop.error}
        onBack={shop.showProduct}
        onCheckout={shop.confirm}
        onStore={store => shop.updateOptions({store})}
        onBonusChange={shop.selectBonus}
      />}
    />
    {shop.error && view === "product" && <p className="store-inline-notice" role="alert">{shop.error}</p>}
    {executorUnavailable && <p className="store-inline-notice" role="alert">{t("error_shop_unavailable")}</p>}
    {activeProduct && <ProductDetails
      product={activeProduct}
      selectedSize={detailsSize}
      onSize={setDetailsSize}
      onBuy={id => { setDetails(null); shop.buy(id, detailsSize); }}
      onClose={() => setDetails(null)}
    />}
  </main>;
}

initializeShopLanguage(argumentsFromLink.get("lang"));

let token = "";
try {
  token = decodeURIComponent(location.hash.slice(1));
} catch {
  // Malformed links fail through the same server authorization as an empty link.
}
createRoot(document.getElementById("root")!).render(<Shop token={token} />);

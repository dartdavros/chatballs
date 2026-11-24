import { useEffect, useMemo, useRef, useState } from "react";

import type { ProductId, ShopCart, ShopOptions, ShopOrder, ShopQuote, StoreData } from "./model";
import { applyShopLanguage, t } from "./language";
import type { ShopMessageKey } from "./messages.ru";
import { ShopRequestError, storefrontApi } from "./shopApi";

const initialOptions: ShopOptions = {productId: "alpine", size: "L", store: "center"};

const errors: Partial<Record<string, ShopMessageKey>> = {
  cart_changed: "error_cart_changed",
  quote_changed: "error_quote_changed",
  stock_unavailable: "error_stock_unavailable",
  bonus_limit: "error_bonus_limit",
  bonuses_unavailable: "error_bonuses_unavailable",
  demo_generation_unavailable: "error_visit_expired",
};

function describe(error: unknown) {
  if (error instanceof ShopRequestError) {
    if (error.status === 403 || error.status === 404) return t("error_visit_expired");
    const message = errors[error.code];
    if (message) return t(message);
  }
  return t("error_shop_unavailable");
}

export function useNorthWindShop(token: string, selection?: Partial<ShopOptions>) {
  const api = useMemo(() => storefrontApi(token), [token]);
  const [data, setData] = useState<StoreData | null>(null);
  const [options, setOptions] = useState(() => ({...initialOptions, ...selection}));
  const [cart, setCart] = useState<ShopCart | null>(null);
  const [quote, setQuote] = useState<ShopQuote | null>(null);
  const [order, setOrder] = useState<ShopOrder | null>(null);
  const [bonus, setBonus] = useState(0);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [view, setView] = useState<"product" | "checkout">("product");
  const [navigationKey, setNavigationKey] = useState(0);
  const requests = useRef(new Map<string, string>());
  const writing = useRef(false);

  useEffect(() => {
    let active = true;
    api<StoreData>("start").then(value => {
      if (!active) return;
      applyShopLanguage(value.language);
      setData(value);
      setCart(value.cart);
      setOrder(value.order);
      if (value.order) setView("checkout");
    }).catch((failure: unknown) => { if (active) setError(describe(failure)); });
    return () => { active = false; };
  }, [api]);

  useEffect(() => {
    if (!cart || order) return;
    let active = true;
    api<ShopQuote>("quote", {product_id: cart.productId, size: cart.size, bonus}).then(value => {
      if (active) setQuote(value);
    }).catch((failure: unknown) => {
      if (active) {
        setError(describe(failure));
        if (bonus && failure instanceof ShopRequestError && failure.status === 409) setBonus(0);
      }
    });
    return () => { active = false; };
  }, [api, cart, bonus, order]);

  async function write<T>(operation: string, values: Record<string, unknown>, onSuccess: (result: T) => void) {
    if (writing.current) return;
    const signature = JSON.stringify([operation, values]);
    const id = requests.current.get(signature) ?? crypto.randomUUID();
    requests.current.set(signature, id);
    writing.current = true;
    setPending(true);
    setError("");
    try {
      onSuccess(await api<T>(operation, values, id));
      requests.current.delete(signature);
    } catch (failure) {
      setError(describe(failure));
      if (failure instanceof ShopRequestError && failure.status === 409) {
        requests.current.delete(signature);
        const next = await api<StoreData>("start").catch(() => null);
        if (next) {
          setData(next);
          setCart(next.cart);
          setOrder(next.order);
          if (next.order) {
            setError("");
            setView("checkout");
          }
        }
      }
    } finally {
      writing.current = false;
      setPending(false);
    }
  }

  function buy(productId: ProductId, size = options.size) {
    void write<ShopCart>("cart", {product_id: productId, size}, next => {
      setCart(next);
      setOrder(null);
      setBonus(0);
      setQuote(null);
      setView("checkout");
      setNavigationKey(current => current + 1);
      window.scrollTo(0, 0);
    });
  }

  function confirm() {
    if (!cart || !quote || bonus !== quote.bonusSpent) return;
    const store = options.store;
    void write<ShopOrder>("checkout", {
      product_id: cart.productId, size: cart.size, bonus, store, revision: quote.revision, confirmed: true,
    }, result => {
      setOrder(result);
      setCart(null);
      setData(previous => previous && ({
        ...previous,
        balance: result.balanceAfter,
        products: previous.products.map(product => product.id === result.productId ? {
          ...product, stock: {
            ...product.stock,
            [result.size]: product.stock[result.size].map(row => row.store === store ? {
              ...row, available: result.stockAfter,
            } : row),
          },
        } : product),
      }));
    });
  }

  function updateOptions(patch: Partial<ShopOptions>) {
    setOptions(previous => ({...previous, ...patch}));
  }

  function selectBonus(enabled: boolean, amount: number) {
    setError("");
    setBonus(enabled ? amount : 0);
  }

  function showProduct() {
    if (order) setOrder(null);
    setView("product");
    setNavigationKey(current => current + 1);
    window.scrollTo(0, 0);
  }

  return {
    data, options, cart, quote, order, bonus, error, pending, view, navigationKey,
    buy, confirm, updateOptions, selectBonus, showProduct,
    showCart: () => setView("checkout"),
  };
}

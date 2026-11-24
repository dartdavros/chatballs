import type { ProductId, ShopOptions, Size, StoreId } from "./model";

const products = new Set<string>(["alpine", "summit", "ridge", "glacier", "freeride", "peak"]);
const sizes = new Set<string>(["M", "L", "XL"]);
const stores = new Set<string>(["center", "gorki"]);

export function pickupLink(query: URLSearchParams): ShopOptions | undefined {
  const productId = query.get("product");
  const size = query.get("size");
  const store = query.get("store");
  if (productId && size && store && products.has(productId) && sizes.has(size) && stores.has(store)) {
    return {productId: productId as ProductId, size: size as Size, store: store as StoreId};
  }
}

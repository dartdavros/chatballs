import type { Customer, Product, ProductId, ShopProduct, Size, StoreId } from "./model";
import { fmt, t } from "./language";

export type { Product, ProductId, Size } from "./model";

const colours: Record<ProductId, string> = {
  alpine: "#326c95",
  summit: "#caa33e",
  ridge: "#647858",
  glacier: "#e8e4db",
  freeride: "#bb6550",
  peak: "#2e3947",
};

export const stores: StoreId[] = ["center", "gorki"];
export const sizes: Size[] = ["M", "L", "XL"];

export const storeLabel = (store: StoreId) => t(`store_${store}`);
export const money = (amount: number) => t("price", {amount: fmt.number(amount)});

export function customerProfile(customer: Customer) {
  const profile = customer === "andrey-after-purchase" ? "andrey" : customer;
  const phones: Record<typeof profile, string> = {
    andrey: "+7 900 000-00-42",
    maria: "+7 900 000-00-43",
    olga: "+7 900 000-00-44",
    school: "+7 900 000-00-45",
  };
  return {name: t(profile), phone: phones[profile]};
}

export function displayProduct(product: ShopProduct, customer: Customer): Product {
  return {
    id: product.id, name: product.name, article: `SL-${product.id.toUpperCase()}`,
    price: customer === "andrey" || customer === "andrey-after-purchase" ? product.personalPrice : product.basePrice,
    basePrice: product.basePrice, color: colours[product.id], colorName: t(`colour_${product.id}`),
    material: t(`material_${product.id}`), description: t(`description_${product.id}`), sizes,
    lining: t("insulation_measure", {amount: fmt.number(product.insulation)}),
    membrane: t("membrane_measure", {amount: fmt.number(product.membrane)}),
    breathability: t("breathability_measure", {amount: fmt.number(product.breathability)}),
    photo: `${import.meta.env.BASE_URL}north-wind/images/${product.id}.png`,
    stockBySize: Object.fromEntries(sizes.map(size => [
      size, Object.fromEntries(product.stock[size].map(row => [row.store, row.available])),
    ])) as Product["stockBySize"],
  };
}

export function displayInventory(product: ShopProduct, size: Size) {
  return product.stock[size].map(row => ({
    store: row.store, address: row.address, available: row.available,
    hours: t("daily_hours", {close: row.closesAt}),
  }));
}

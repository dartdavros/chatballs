import type { Product, ProductOffer } from "../../../types";

export type ProductTab = "overview" | "offers" | "knowledge" | "channels" | "fulfillment";

export const productTabs: Array<{ key: ProductTab; label: string }> = [
  { key: "overview", label: "Обзор" },
  { key: "offers", label: "Предложения и цены" },
  { key: "knowledge", label: "База знаний" },
  { key: "channels", label: "Каналы" },
  { key: "fulfillment", label: "Доступ продукта" },
];

export function productKind(product: Product) {
  const offer = product.offers.find((item) => item.isActive && item.fulfillmentType !== "SUPPORT_EXTENSION");
  if (!offer) return "—";
  const fulfillment = offer.fulfillmentType === "SAAS_ACCESS" ? "SaaS" : "Коробка";
  const payment = offer.paymentType === "SUBSCRIPTION" ? "подписка" : "разовая";
  return `${fulfillment} · ${payment}`;
}

export function offerType(offer: ProductOffer) {
  if (offer.fulfillmentType === "SUPPORT_EXTENSION") return "продление";
  return offer.paymentType === "SUBSCRIPTION" ? "подписка" : "разовая";
}

export function formatProductDate(value: string) {
  return new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "long", year: "numeric" }).format(new Date(value));
}

import type { Product } from "../../types";

export function productDetails(product: Product) {
  return {
    sub: product.siteUrl || product.code,
    offers: product.offers.filter((offer) => offer.isActive).map((offer) => ({
      name: offer.name,
      type: offer.fulfillmentType === "SUPPORT_EXTENSION" ? "продление" : offer.paymentType === "SUBSCRIPTION" ? "подписка" : "разовая",
      price: offer.prices.filter((price) => price.isActive).map(formatPrice).join(" · ") || "—",
    })),
    sales: {
      today: { n: 0, sum: "₽0" },
      d7: { n: 0, sum: "₽0" },
      d30: { n: 0, sum: "₽0" },
    },
  };
}

export function formatPrice(price: Product["offers"][number]["prices"][number]) {
  const amount = new Intl.NumberFormat("ru-RU", { style: "currency", currency: price.currency, maximumFractionDigits: 0 }).format(price.amountMinor / 100);
  const period = { ONE_TIME: "разово", MONTH: "/ мес", YEAR: "/ год" }[price.billingPeriod];
  return price.billingPeriod === "ONE_TIME" ? amount : `${amount} ${period}`;
}

import type { Product } from "../../types";

export function productDetails(product: Product) {
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

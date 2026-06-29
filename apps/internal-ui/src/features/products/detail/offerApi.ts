import { api } from "../../../api/client";

// Каталог (offers + версии цен) живёт в Хабе (ADR-HUB-0018).
// Роуты продуктов смонтированы под /api/v1/company/.
function base(productId: number): string {
  return `/api/v1/company/products/${productId}`;
}

export type OfferBody = {
  code?: string;
  name: string;
  description: string;
  fulfillmentType: string;
  paymentType: string;
  isActive: boolean;
  aiOfferable: boolean;
  primaryBoxOfferId: number | null;
};

export type PriceBody = {
  amountMinor: number;
  billingPeriod: string;
  currency: string;
  validFrom?: string;
};

export async function createOffer(productId: number, body: OfferBody): Promise<void> {
  await api(`${base(productId)}/offers/`, { method: "POST", body: JSON.stringify(body) });
}

export async function updateOffer(productId: number, offerId: number, body: OfferBody): Promise<void> {
  await api(`${base(productId)}/offers/${offerId}/`, { method: "PATCH", body: JSON.stringify(body) });
}

export async function addPriceVersion(productId: number, offerId: number, body: PriceBody): Promise<void> {
  await api(`${base(productId)}/offers/${offerId}/prices/`, { method: "POST", body: JSON.stringify(body) });
}

export const fulfillmentOptions: Array<[string, string]> = [
  ["SAAS_ACCESS", "SaaS-доступ"],
  ["BOX_LICENSE", "Коробочная лицензия"],
  ["SUPPORT_EXTENSION", "Продление поддержки"],
];

export const paymentOptions: Array<[string, string]> = [
  ["ONE_TIME", "Разовая оплата"],
  ["SUBSCRIPTION", "Подписка"],
];

export const billingOptions: Array<[string, string]> = [
  ["ONE_TIME", "Разово"],
  ["MONTH", "Месяц"],
  ["YEAR", "Год"],
];

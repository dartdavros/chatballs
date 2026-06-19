import { describe, expect, it } from "vitest";

import type { Product } from "../../types";
import { formatPrice, productDetails } from "./model";

const product: Product = {
  id: 1,
  code: "foxray",
  name: "Foxray",
  status: "ACTIVE",
  siteUrl: "https://foxray.pro",
  summary: "SaaS",
  salesDescription: "",
  departments: [],
  createdAt: "2026-06-19T00:00:00Z",
  updatedAt: "2026-06-19T00:00:00Z",
  offers: [
    {
      id: 10,
      code: "pro",
      name: "Pro",
      description: "",
      fulfillmentType: "SAAS_ACCESS",
      paymentType: "SUBSCRIPTION",
      primaryBoxOfferId: null,
      isActive: true,
      aiOfferable: true,
      prices: [
        { id: 20, version: 1, amountMinor: 490_000, currency: "RUB", billingPeriod: "MONTH", validFrom: "2026-06-19T00:00:00Z", validUntil: null, isActive: true },
        { id: 21, version: 2, amountMinor: 4_704_000, currency: "RUB", billingPeriod: "YEAR", validFrom: "2026-06-19T00:00:00Z", validUntil: null, isActive: true },
      ],
    },
  ],
};

describe("product model", () => {
  it("builds tariffs from API data instead of product code", () => {
    const details = productDetails({ ...product, code: "any-product" });

    expect(details.offers).toHaveLength(1);
    expect(details.offers[0].name).toBe("Pro");
    expect(details.offers[0].price).toContain("мес");
    expect(details.offers[0].price).toContain("год");
  });

  it("formats one-time and recurring price periods", () => {
    expect(formatPrice(product.offers[0].prices[0])).toContain("/ мес");
    expect(formatPrice({ ...product.offers[0].prices[0], billingPeriod: "ONE_TIME" })).not.toContain("/");
  });
});

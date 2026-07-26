import { describe, expect, it } from "vitest";

import { paginationItems } from "./SalesClientsPagination";

describe("paginationItems", () => {
  it("returns every page for a short list", () => {
    expect(paginationItems(1, 4)).toEqual([1, 2, 3, 4]);
  });

  it("keeps the current page and boundaries for a long list", () => {
    expect(paginationItems(5, 10)).toEqual([
      1,
      "ellipsis",
      4,
      5,
      6,
      "ellipsis",
      10,
    ]);
  });

  it("does not add a leading ellipsis next to the first page", () => {
    expect(paginationItems(2, 10)).toEqual([
      1,
      2,
      3,
      "ellipsis",
      10,
    ]);
  });
});

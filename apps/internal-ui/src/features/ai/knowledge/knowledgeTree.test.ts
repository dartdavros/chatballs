import { describe, expect, it } from "vitest";

import type { KnowledgeCategory } from "./types";
import {
  buildCategoryTree,
  planCategoryDrop,
} from "../../../shared/content-library/categoryManagementModel";
import {
  knowledgeCategoryPath,
  totalKnowledgeCount,
} from "./knowledgeTree";

const categories: KnowledgeCategory[] = [
  { id: 4, name: "Лицензирование", parentId: 2, sortOrder: 20, isSystem: false, knowledgeCount: 3 },
  { id: 1, name: "Без категории", parentId: null, sortOrder: 0, isSystem: true, knowledgeCount: 4 },
  { id: 3, name: "Продажи", parentId: null, sortOrder: 20, isSystem: false, knowledgeCount: 9 },
  { id: 2, name: "Продукты", parentId: null, sortOrder: 10, isSystem: false, knowledgeCount: 14 },
  { id: 5, name: "Acme", parentId: 2, sortOrder: 10, isSystem: false, knowledgeCount: 8 },
];

describe("knowledge category tree", () => {
  it("builds a deterministic hierarchy and aggregate total", () => {
    const tree = buildCategoryTree(categories.map((item) => ({
      id: item.id,
      name: item.name,
      parentId: item.parentId,
      sortOrder: item.sortOrder,
      count: item.knowledgeCount ?? 0,
      isSystem: item.isSystem,
    })));

    expect(tree.map((category) => category.id)).toEqual([1, 2, 3]);
    expect(tree[1].children.map((category) => category.id)).toEqual([5, 4]);
    expect(totalKnowledgeCount(categories)).toBe(27);
  });

  it("builds the full category path", () => {
    expect(knowledgeCategoryPath(categories, 4)).toBe("Продукты / Лицензирование");
  });

  it("plans reparenting and rejects cycles and system moves", () => {
    const managed = categories.map((item) => ({
      id: item.id,
      name: item.name,
      parentId: item.parentId,
      sortOrder: item.sortOrder,
      count: item.knowledgeCount ?? 0,
      isSystem: item.isSystem,
    }));
    expect(planCategoryDrop(managed, 3, 5, "inside")).toEqual([
      { id: 3, parentId: 5, sortOrder: 10 },
    ]);
    expect(planCategoryDrop(managed, 2, 4, "inside")).toEqual([]);
    expect(planCategoryDrop(managed, 1, 3, "after")).toEqual([]);
  });
});

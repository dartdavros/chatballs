import type { KnowledgeCategory } from "./types";

export type KnowledgeCategoryNode = KnowledgeCategory & {
  children: KnowledgeCategoryNode[];
};

export type CategoryDropPosition = "after" | "before" | "inside";

export type CategoryOrderUpdate = {
  id: number;
  parentId: number | null;
  sortOrder: number;
};

function categoryOrder(left: KnowledgeCategory, right: KnowledgeCategory): number {
  return left.sortOrder - right.sortOrder
    || left.name.localeCompare(right.name, "ru")
    || left.id - right.id;
}

export function buildKnowledgeCategoryTree(
  categories: KnowledgeCategory[],
): KnowledgeCategoryNode[] {
  const nodes = new Map<number, KnowledgeCategoryNode>(
    categories.map((category) => [category.id, { ...category, children: [] }]),
  );
  const roots: KnowledgeCategoryNode[] = [];

  for (const node of nodes.values()) {
    const parent = node.parentId === null ? undefined : nodes.get(node.parentId);
    if (parent && parent.id !== node.id) parent.children.push(node);
    else roots.push(node);
  }

  const sortNodes = (items: KnowledgeCategoryNode[]) => {
    items.sort(categoryOrder);
    items.forEach((item) => sortNodes(item.children));
  };
  sortNodes(roots);
  return roots;
}

export function totalKnowledgeCount(categories: KnowledgeCategory[]): number {
  return categories
    .filter((category) => category.parentId === null)
    .reduce((total, category) => total + (category.knowledgeCount ?? 0), 0);
}

export function knowledgeCategoryPath(
  categories: KnowledgeCategory[],
  categoryId: number,
): string {
  const byId = new Map(categories.map((category) => [category.id, category]));
  const path: string[] = [];
  const visited = new Set<number>();
  let current = byId.get(categoryId);

  while (current && !visited.has(current.id)) {
    visited.add(current.id);
    path.unshift(current.name);
    current = current.parentId === null ? undefined : byId.get(current.parentId);
  }
  return path.join(" / ");
}

function descendantsOf(categories: KnowledgeCategory[], categoryId: number): Set<number> {
  const children = new Map<number, number[]>();
  categories.forEach((category) => {
    if (category.parentId === null) return;
    children.set(category.parentId, [...(children.get(category.parentId) ?? []), category.id]);
  });
  const descendants = new Set<number>();
  const pending = [...(children.get(categoryId) ?? [])];
  while (pending.length > 0) {
    const next = pending.pop();
    if (next === undefined || descendants.has(next)) continue;
    descendants.add(next);
    pending.push(...(children.get(next) ?? []));
  }
  return descendants;
}

export function planCategoryDrop(
  categories: KnowledgeCategory[],
  draggedId: number,
  targetId: number,
  position: CategoryDropPosition,
): CategoryOrderUpdate[] {
  const dragged = categories.find((category) => category.id === draggedId);
  const target = categories.find((category) => category.id === targetId);
  if (!dragged || !target || dragged.isSystem || dragged.id === target.id) return [];
  if (descendantsOf(categories, dragged.id).has(target.id)) return [];
  if (position === "inside" && target.isSystem) return [];

  const parentId = position === "inside" ? target.id : target.parentId;
  const siblings = categories
    .filter((category) => category.parentId === parentId && category.id !== dragged.id)
    .sort(categoryOrder);
  const targetIndex = position === "inside"
    ? siblings.length
    : Math.max(0, siblings.findIndex((category) => category.id === target.id));
  const insertIndex = position === "after" ? targetIndex + 1 : targetIndex;
  siblings.splice(insertIndex, 0, { ...dragged, parentId });

  return siblings.flatMap((category, index) => {
    const sortOrder = (index + 1) * 10;
    if (
      category.id !== dragged.id
      && category.parentId === categories.find((item) => item.id === category.id)?.parentId
      && category.sortOrder === sortOrder
    ) return [];
    return [{ id: category.id, parentId, sortOrder }];
  });
}

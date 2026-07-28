export type ManagedContentCategory = {
  id: number;
  name: string;
  parentId: number | null;
  sortOrder: number;
  count: number;
  isSystem?: boolean;
};

export type ManagedContentCategoryNode = ManagedContentCategory & {
  children: ManagedContentCategoryNode[];
};

export type CategoryDropPosition = "after" | "before" | "inside";

export type CategoryOrderUpdate = {
  id: number;
  parentId: number | null;
  sortOrder: number;
};

function categoryOrder(left: ManagedContentCategory, right: ManagedContentCategory) {
  return left.sortOrder - right.sortOrder
    || left.name.localeCompare(right.name, "ru")
    || left.id - right.id;
}

export function buildCategoryTree(
  categories: ManagedContentCategory[],
): ManagedContentCategoryNode[] {
  const nodes = new Map(categories.map((category) => [
    category.id,
    { ...category, children: [] } as ManagedContentCategoryNode,
  ]));
  const roots: ManagedContentCategoryNode[] = [];
  nodes.forEach((node) => {
    const parent = node.parentId === null ? undefined : nodes.get(node.parentId);
    if (parent && parent.id !== node.id) parent.children.push(node);
    else roots.push(node);
  });
  const sort = (items: ManagedContentCategoryNode[]) => {
    items.sort(categoryOrder);
    items.forEach((item) => sort(item.children));
  };
  sort(roots);
  return roots;
}

function descendantsOf(categories: ManagedContentCategory[], categoryId: number) {
  const descendants = new Set<number>();
  const pending = categories.filter((item) => item.parentId === categoryId).map((item) => item.id);
  while (pending.length) {
    const next = pending.pop()!;
    if (descendants.has(next)) continue;
    descendants.add(next);
    pending.push(...categories.filter((item) => item.parentId === next).map((item) => item.id));
  }
  return descendants;
}

export function planCategoryDrop(
  categories: ManagedContentCategory[],
  draggedId: number,
  targetId: number,
  position: CategoryDropPosition,
): CategoryOrderUpdate[] {
  const dragged = categories.find((item) => item.id === draggedId);
  const target = categories.find((item) => item.id === targetId);
  if (!dragged || !target || dragged.isSystem || dragged.id === target.id) return [];
  if (descendantsOf(categories, dragged.id).has(target.id)) return [];
  if (position === "inside" && target.isSystem) return [];
  const parentId = position === "inside" ? target.id : target.parentId;
  const siblings = categories
    .filter((item) => item.parentId === parentId && item.id !== dragged.id)
    .sort(categoryOrder);
  const targetIndex = position === "inside"
    ? siblings.length
    : Math.max(0, siblings.findIndex((item) => item.id === target.id));
  siblings.splice(position === "after" ? targetIndex + 1 : targetIndex, 0, { ...dragged, parentId });
  return siblings.flatMap((item, index) => {
    const sortOrder = (index + 1) * 10;
    const current = categories.find((category) => category.id === item.id);
    return current?.parentId === parentId && current.sortOrder === sortOrder
      ? []
      : [{ id: item.id, parentId, sortOrder }];
  });
}

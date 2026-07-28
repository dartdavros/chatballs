import type { KnowledgeCategory } from "./types";

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

import { useCallback, useEffect, useRef, useState } from "react";

import {
  fetchKnowledgeCategories,
  fetchKnowledgeList,
  type KnowledgeCategory,
  type KnowledgeDepartmentReference,
  type KnowledgeItem,
  type KnowledgeListFilters,
  type KnowledgeVisibility,
} from "./model";

export type KnowledgeLibraryFilterState = {
  category?: number;
  department?: number;
  isEnabled?: boolean;
  search: string;
  visibility?: KnowledgeVisibility;
};

export function useKnowledgeLibrary() {
  const [items, setItems] = useState<KnowledgeItem[]>([]);
  const [categories, setCategories] = useState<KnowledgeCategory[]>([]);
  const [knownDepartments, setKnownDepartments] = useState<KnowledgeDepartmentReference[]>([]);
  const [filters, setFilters] = useState<KnowledgeLibraryFilterState>({ search: "" });
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [itemsLoading, setItemsLoading] = useState(true);
  const [categoriesLoading, setCategoriesLoading] = useState(true);
  const [itemsError, setItemsError] = useState(false);
  const [categoriesError, setCategoriesError] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(() => new Set());
  const requestId = useRef(0);

  useEffect(() => {
    const timeout = window.setTimeout(() => setDebouncedSearch(filters.search.trim()), 250);
    return () => window.clearTimeout(timeout);
  }, [filters.search]);

  const reloadCategories = useCallback(async () => {
    setCategoriesLoading(true);
    setCategoriesError(false);
    try {
      const payload = await fetchKnowledgeCategories();
      setCategories(payload.items);
    } catch {
      setCategoriesError(true);
    } finally {
      setCategoriesLoading(false);
    }
  }, []);

  const reloadItems = useCallback(async (activeFilters: KnowledgeListFilters) => {
    const activeRequest = ++requestId.current;
    setItemsLoading(true);
    setItemsError(false);
    try {
      const payload = await fetchKnowledgeList(activeFilters);
      if (activeRequest !== requestId.current) return;
      setItems(payload.items);
      setKnownDepartments((current) => {
        const byId = new Map(current.map((department) => [department.id, department]));
        payload.items.forEach((item) => item.departments.forEach((department) => {
          byId.set(department.id, department);
        }));
        return [...byId.values()].sort((left, right) => left.name.localeCompare(right.name, "ru"));
      });
    } catch {
      if (activeRequest === requestId.current) setItemsError(true);
    } finally {
      if (activeRequest === requestId.current) setItemsLoading(false);
    }
  }, []);

  useEffect(() => {
    void reloadCategories();
  }, [reloadCategories]);

  useEffect(() => {
    if (
      !categoriesLoading
      && filters.category !== undefined
      && !categories.some((category) => category.id === filters.category)
    ) {
      setFilters((current) => ({ ...current, category: undefined }));
    }
  }, [categories, categoriesLoading, filters.category]);

  useEffect(() => {
    void reloadItems({
      category: filters.category,
      department: filters.department,
      isEnabled: filters.isEnabled,
      search: debouncedSearch,
      visibility: filters.visibility,
    });
  }, [debouncedSearch, filters.category, filters.department, filters.isEnabled, filters.visibility, reloadItems]);

  const updateFilter = useCallback(<TKey extends keyof KnowledgeLibraryFilterState>(
    key: TKey,
    value: KnowledgeLibraryFilterState[TKey],
  ) => {
    setFilters((current) => ({ ...current, [key]: value }));
  }, []);

  const toggleSelected = useCallback((knowledgeId: number) => {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (next.has(knowledgeId)) next.delete(knowledgeId);
      else next.add(knowledgeId);
      return next;
    });
  }, []);

  const toggleVisible = useCallback(() => {
    setSelectedIds((current) => {
      const visibleIds = items.map((item) => item.id);
      const allSelected = visibleIds.length > 0 && visibleIds.every((id) => current.has(id));
      const next = new Set(current);
      visibleIds.forEach((id) => allSelected ? next.delete(id) : next.add(id));
      return next;
    });
  }, [items]);

  const reload = useCallback(async () => {
    await Promise.all([
      reloadCategories(),
      reloadItems({
        category: filters.category,
        department: filters.department,
        isEnabled: filters.isEnabled,
        search: debouncedSearch,
        visibility: filters.visibility,
      }),
    ]);
  }, [debouncedSearch, filters, reloadCategories, reloadItems]);

  return {
    categories,
    categoriesError,
    categoriesLoading,
    filters,
    items,
    itemsError,
    itemsLoading,
    knownDepartments,
    reload,
    reloadCategories,
    selectedIds,
    toggleSelected,
    toggleVisible,
    updateFilter,
  };
}

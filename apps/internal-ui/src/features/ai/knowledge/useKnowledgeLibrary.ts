import { useCallback, useEffect, useMemo, useState } from "react";

import { useDebounced } from "../../../shared/useDebounced";
import { usePagedResource } from "../../../shared/usePagedResource";
import {
  fetchKnowledgeCategories,
  fetchKnowledgeList,
  type KnowledgeCategory,
} from "./model";
import { t } from "../../../i18n";

// Библиотека знаний: страница, ветка категорий, агент, состояние и поиск —
// всё на сервере. Раньше ветку и агента отбирал браузер по всему набору,
// поэтому список приходилось запрашивать целиком.

export type KnowledgeLibraryFilterState = {
  category?: number;
  isEnabled?: boolean;
  search: string;
  /** Идентификаторы AIAgent из фильтра «Агент». */
  agents: number[];
};

const EMPTY_FILTERS: KnowledgeLibraryFilterState = { search: "", agents: [] };

export function useKnowledgeLibrary() {
  const [categories, setCategories] = useState<KnowledgeCategory[]>([]);
  const [filters, setFilters] = useState<KnowledgeLibraryFilterState>(EMPTY_FILTERS);
  const [categoriesLoading, setCategoriesLoading] = useState(true);
  const [categoriesError, setCategoriesError] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(() => new Set());
  const settledSearch = useDebounced(filters.search.trim());

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

  const request = useMemo(
    () => ({
      category: filters.category,
      isEnabled: filters.isEnabled,
      search: settledSearch,
      agents: filters.agents,
    }),
    [filters.agents, filters.category, filters.isEnabled, settledSearch],
  );
  const load = useCallback((page: number) => fetchKnowledgeList(request, page), [request]);
  const page = usePagedResource(load, request, t("ai.could_not_load_knowledge"));

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

  const clearSelected = useCallback(() => setSelectedIds(new Set()), []);

  /** Действие из меню строки работает над одним знанием: выбор заменяется. */
  const selectOnly = useCallback((knowledgeId: number) => setSelectedIds(new Set([knowledgeId])), []);

  const items = page.items;
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
    await Promise.all([reloadCategories(), page.reload()]);
  }, [page, reloadCategories]);

  return {
    categories,
    categoriesError,
    categoriesLoading,
    clearSelected,
    filters,
    items,
    itemsError: Boolean(page.errorText),
    itemsLoading: page.loading,
    page: page.page,
    pageCount: page.pageCount,
    total: page.total,
    setPage: page.setPage,
    reload,
    reloadCategories,
    selectOnly,
    selectedIds,
    toggleSelected,
    toggleVisible,
    updateFilter,
  };
}

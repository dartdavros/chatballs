import { useCallback, useEffect, useRef, useState } from "react";
import { t } from "../i18n";

// Постраничный список: страницу и фильтры считает сервер, здесь — только
// состояние страницы и защита от гонок. Смена любого фильтра возвращает на
// первую страницу: иначе человек остаётся на седьмой странице набора из двух
// записей.

export type PagedPayload<T> = {
  items: T[];
  page: number;
  pageSize: number;
  total: number;
  pageCount: number;
};

const EMPTY: PagedPayload<never> = { items: [], page: 1, pageSize: 0, total: 0, pageCount: 1 };

export type PagedResource<T, P> = {
  /** Ответ целиком: у некоторых списков в нём есть и свои блоки — например
   *  справочники фильтров журнала аудита. */
  payload: P | null;
  items: T[];
  page: number;
  pageCount: number;
  pageSize: number;
  total: number;
  loading: boolean;
  errorText: string;
  setPage: (page: number) => void;
  reload: () => Promise<void>;
};

// Тип записи выводится из самого ответа: у части списков в нём есть и свои
// блоки (например справочники фильтров журнала аудита), поэтому параметр — ответ.
export function usePagedResource<P extends PagedPayload<unknown>>(
  load: (page: number) => Promise<P>,
  filters: unknown,
  errorMessage = t("shared.could_not_load_list"),
): PagedResource<P["items"][number], P> {
  const [payload, setPayload] = useState<P | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorText, setErrorText] = useState("");
  // Загрузчик пересоздаётся на каждый рендер — держим его в ref, чтобы эффект
  // перезапускался только на смену страницы и фильтров.
  const loadRef = useRef(load);
  loadRef.current = load;
  // Ответ медленного запроса не должен затирать более свежий.
  const generation = useRef(0);
  const key = JSON.stringify(filters ?? null);
  // Страница принадлежит набору фильтров: при их смене она сбрасывается прямо
  // здесь, а не эффектом — иначе первый запрос ушёл бы за старой страницей
  // нового набора и тут же был бы перезапрошен.
  const [pageState, setPageState] = useState({ key, page: 1 });
  const page = pageState.key === key ? pageState.page : 1;
  if (pageState.key !== key) setPageState({ key, page: 1 });
  const setPage = useCallback(
    (next: number) => setPageState((current) => ({ key: current.key, page: next })),
    [],
  );

  const reload = useCallback(async () => {
    const current = ++generation.current;
    setLoading(true);
    try {
      const next = await loadRef.current(page);
      if (current !== generation.current) return;
      setPayload(next);
      // Сервер мог отдать другую страницу — например последнюю, если записи
      // удалили из-под открытой. Тогда и состояние переходит на неё, иначе
      // «дальше» листало бы от несуществующего номера.
      setPageState((state) => (state.page === next.page ? state : { key: state.key, page: next.page }));
      setErrorText("");
    } catch {
      if (current === generation.current) setErrorText(errorMessage);
    } finally {
      if (current === generation.current) setLoading(false);
    }
  }, [errorMessage, page]);

  useEffect(() => {
    void reload();
  }, [key, reload]);

  // Пока ответа нет, список ведёт себя как пустая первая страница.
  const current = payload ?? (EMPTY as PagedPayload<P["items"][number]>);
  return {
    payload,
    items: current.items,
    // Сервер возвращает существующую страницу: если записи удалили из-под
    // открытой страницы, он отдаст последнюю, и подвал покажет именно её.
    page: current.page,
    pageCount: current.pageCount,
    pageSize: current.pageSize,
    total: current.total,
    loading,
    errorText,
    setPage,
    reload,
  };
}

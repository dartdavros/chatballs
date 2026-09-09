import { useCallback, useMemo, useState } from "react";

import { useDebounced } from "../../../shared/useDebounced";
import { usePagedResource } from "../../../shared/usePagedResource";
import { fetchClients, type ClientsQuery } from "./api";
import type { ClientChannelCode, ClientDropdown, ClientSortKey } from "./model";
import { toSalesClient, toSalesClientRow } from "./model";
import { t } from "../../../i18n";

export type SalesClientsState = ReturnType<typeof useSalesClients>;

// Фильтры списка контактов (кадры K1/K2): поиск, каналы, агенты и чип
// «С открытым диалогом». Фильтра по продуктам нет (ADR-CHATBALLS-0041).
// Всё это — параметры запроса: страница приходит с сервера уже отобранной.

export function useSalesClients() {
  const [query, setQueryState] = useState("");
  const [agentFilter, setAgentFilter] = useState<number[]>([]);
  const [channelFilter, setChannelFilter] = useState<ClientChannelCode[]>([]);
  const [openOnly, setOpenOnly] = useState(false);
  const [sortKey, setSortKey] = useState<ClientSortKey>("last");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [menu, setMenu] = useState<string | null>(null);
  const [dropdown, setDropdown] = useState<ClientDropdown | null>(null);
  const settledQuery = useDebounced(query);

  const request: ClientsQuery = useMemo(
    () => ({ query: settledQuery, agentFilter, channelFilter, openOnly, sortKey, sortDir }),
    [agentFilter, channelFilter, openOnly, settledQuery, sortDir, sortKey],
  );
  const load = useCallback((page: number) => fetchClients(request, page), [request]);
  const page = usePagedResource(load, request, t("sales.could_not_load_contacts"));
  const rows = useMemo(
    () => page.items.map((item) => toSalesClientRow(toSalesClient(item))),
    [page.items],
  );

  function setQuery(value: string) {
    setQueryState(value);
    setMenu(null);
  }

  function toggleAgent(id: number) {
    setAgentFilter((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
  }

  function toggleChannel(code: string) {
    setChannelFilter((current) => current.includes(code as ClientChannelCode) ? current.filter((item) => item !== code) : [...current, code as ClientChannelCode]);
  }

  function toggleDropdown(nextDropdown: ClientDropdown) {
    setDropdown((current) => current === nextDropdown ? null : nextDropdown);
    setMenu(null);
  }

  function sortBy(nextSortKey: ClientSortKey) {
    setSortKey(nextSortKey);
    setSortDir((current) => sortKey === nextSortKey && current === "asc" ? "desc" : "asc");
    setMenu(null);
  }

  function reset() {
    setQueryState("");
    setAgentFilter([]);
    setChannelFilter([]);
    setOpenOnly(false);
    setMenu(null);
    setDropdown(null);
  }

  return {
    rows,
    request,
    loading: page.loading,
    errorText: page.errorText,
    total: page.total,
    // Кадр K2: «Сбросить» и счётчик «6 из 128» показываются только при фильтре.
    filtered: Boolean(query.trim()) || agentFilter.length > 0 || channelFilter.length > 0 || openOnly,
    page: page.page,
    pageCount: page.pageCount,
    pageSize: page.pageSize,
    setPage: page.setPage,
    reload: page.reload,
    query,
    agentFilter,
    channelFilter,
    openOnly,
    dropdown,
    menu,
    sortKey,
    sortDir,
    setMenu,
    setQuery,
    toggleAgent,
    toggleChannel,
    toggleDropdown,
    setDropdown,
    closeDropdown: () => setDropdown(null),
    toggleOpenOnly: () => { setOpenOnly((current) => !current); setMenu(null); setDropdown(null); },
    sortBy,
    reset,
  };
}

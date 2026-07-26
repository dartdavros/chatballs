import { useEffect, useMemo, useState } from "react";

import type { ClientChannelCode, ClientDropdown, ClientProductCode, ClientSortKey, ClientStatus, SalesClient } from "./model";
import { toSalesClientRow } from "./model";

export type SalesClientsState = ReturnType<typeof useSalesClients>;

export function useSalesClients(salesClients: SalesClient[]) {
  const [query, setQueryState] = useState("");
  const [productFilter, setProductFilter] = useState<ClientProductCode[]>([]);
  const [channelFilter, setChannelFilter] = useState<ClientChannelCode[]>([]);
  const [openOnly, setOpenOnly] = useState(false);
  // Фильтр по статусу контакта: null — все, иначе только лиды/клиенты.
  const [statusFilter, setStatusFilter] = useState<ClientStatus | null>(null);
  const [sortKey, setSortKey] = useState<ClientSortKey>("last");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [menu, setMenu] = useState<string | null>(null);
  const [dropdown, setDropdown] = useState<ClientDropdown | null>(null);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const filteredRows = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    const filtered = salesClients.filter((client) => {
      return (!normalizedQuery || client.name.toLowerCase().includes(normalizedQuery) || client.email.toLowerCase().includes(normalizedQuery) || client.phone.includes(normalizedQuery) || client.username.toLowerCase().includes(normalizedQuery))
        && (productFilter.length === 0 || client.products.some((product) => productFilter.includes(product)))
        && (channelFilter.length === 0 || client.channels.some((channel) => channelFilter.includes(channel)))
        && (!openOnly || client.openDialogs > 0)
        && (statusFilter === null || client.status === statusFilter);
    });
    const key = { last: "last", open: "openDialogs", orders: "orders", total: "total" } satisfies Record<ClientSortKey, keyof typeof salesClients[number]>;
    return [...filtered]
      .sort((left, right) => sortDir === "asc" ? Number(left[key[sortKey]]) - Number(right[key[sortKey]]) : Number(right[key[sortKey]]) - Number(left[key[sortKey]]))
      .map(toSalesClientRow);
  }, [salesClients, statusFilter, channelFilter, openOnly, productFilter, query, sortDir, sortKey]);
  const pageCount = Math.max(1, Math.ceil(filteredRows.length / pageSize));
  const rows = useMemo(
    () => filteredRows.slice((page - 1) * pageSize, page * pageSize),
    [filteredRows, page],
  );

  useEffect(() => {
    setPage((current) => Math.min(current, pageCount));
  }, [pageCount]);

  function setQuery(value: string) {
    setQueryState(value);
    setPage(1);
    setMenu(null);
  }

  function toggleProduct(code: string) {
    setPage(1);
    setProductFilter((current) => current.includes(code as ClientProductCode) ? current.filter((item) => item !== code) : [...current, code as ClientProductCode]);
  }

  function toggleChannel(code: string) {
    setPage(1);
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
    setProductFilter([]);
    setChannelFilter([]);
    setOpenOnly(false);
    setStatusFilter(null);
    setPage(1);
    setMenu(null);
    setDropdown(null);
  }

  return {
    rows,
    filteredRows,
    filteredCount: filteredRows.length,
    page,
    pageCount,
    setPage,
    query,
    productFilter,
    channelFilter,
    openOnly,
    statusFilter,
    dropdown,
    menu,
    setMenu,
    setQuery,
    toggleProduct,
    toggleChannel,
    toggleDropdown,
    setDropdown,
    closeDropdown: () => setDropdown(null),
    toggleOpenOnly: () => { setOpenOnly((current) => !current); setPage(1); setMenu(null); setDropdown(null); },
    // Повторный клик по активному статусу снимает фильтр (возврат к «все»).
    toggleStatus: (status: ClientStatus) => { setStatusFilter((current) => (current === status ? null : status)); setPage(1); setMenu(null); setDropdown(null); },
    sortBy,
    sortArrow: (key: ClientSortKey) => sortKey === key ? (sortDir === "asc" ? "↑" : "↓") : "",
    reset,
  };
}

import { useEffect, useMemo, useState } from "react";

import type { ClientChannelCode, ClientDropdown, ClientSortKey, SalesClient } from "./model";
import { toSalesClientRow } from "./model";

export type SalesClientsState = ReturnType<typeof useSalesClients>;

// Фильтры списка контактов (кадры K1/K2): поиск, каналы, агенты и чип
// «С открытым диалогом». Фильтра по продуктам нет (ADR-CHATBALLS-0041).

export function useSalesClients(salesClients: SalesClient[]) {
  const [query, setQueryState] = useState("");
  const [agentFilter, setAgentFilter] = useState<number[]>([]);
  const [channelFilter, setChannelFilter] = useState<ClientChannelCode[]>([]);
  const [openOnly, setOpenOnly] = useState(false);
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
        && (agentFilter.length === 0 || client.agents.some((agent) => agentFilter.includes(agent.id)))
        && (channelFilter.length === 0 || client.channels.some((channel) => channelFilter.includes(channel)))
        && (!openOnly || client.openDialogs > 0);
    });
    const key = { last: "last", open: "openDialogs" } satisfies Record<ClientSortKey, keyof typeof salesClients[number]>;
    return [...filtered]
      .sort((left, right) => sortDir === "asc" ? Number(left[key[sortKey]]) - Number(right[key[sortKey]]) : Number(right[key[sortKey]]) - Number(left[key[sortKey]]))
      .map(toSalesClientRow);
  }, [salesClients, agentFilter, channelFilter, openOnly, query, sortDir, sortKey]);
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

  function toggleAgent(id: number) {
    setPage(1);
    setAgentFilter((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
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
    setAgentFilter([]);
    setChannelFilter([]);
    setOpenOnly(false);
    setPage(1);
    setMenu(null);
    setDropdown(null);
  }

  return {
    rows,
    filteredRows,
    filteredCount: filteredRows.length,
    // Кадр K2: «Сбросить» и счётчик «6 из 128» показываются только при фильтре.
    filtered: Boolean(query.trim()) || agentFilter.length > 0 || channelFilter.length > 0 || openOnly,
    page,
    pageCount,
    pageSize,
    setPage,
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
    toggleOpenOnly: () => { setOpenOnly((current) => !current); setPage(1); setMenu(null); setDropdown(null); },
    sortBy,
    reset,
  };
}

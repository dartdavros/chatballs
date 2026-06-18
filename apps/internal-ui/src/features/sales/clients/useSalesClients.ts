import { useMemo, useState } from "react";

import type { ClientChannelCode, ClientDropdown, ClientProductCode, ClientSortKey } from "./model";
import { salesClients, toSalesClientRow } from "./model";

export type SalesClientsState = ReturnType<typeof useSalesClients>;

export function useSalesClients() {
  const [query, setQueryState] = useState("");
  const [productFilter, setProductFilter] = useState<ClientProductCode[]>([]);
  const [channelFilter, setChannelFilter] = useState<ClientChannelCode[]>([]);
  const [openOnly, setOpenOnly] = useState(false);
  const [buyerOnly, setBuyerOnly] = useState(false);
  const [sortKey, setSortKey] = useState<ClientSortKey>("last");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [menu, setMenu] = useState<{ id: string; left: number; top: number } | null>(null);
  const [dropdown, setDropdown] = useState<ClientDropdown | null>(null);

  const rows = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    const filtered = salesClients.filter((client) => {
      return (!normalizedQuery || client.name.toLowerCase().includes(normalizedQuery) || client.email.toLowerCase().includes(normalizedQuery))
        && (productFilter.length === 0 || client.products.some((product) => productFilter.includes(product)))
        && (channelFilter.length === 0 || client.channels.some((channel) => channelFilter.includes(channel)))
        && (!openOnly || client.openDialogs > 0)
        && (!buyerOnly || client.orders > 0);
    });
    const key = { last: "last", open: "openDialogs", orders: "orders", total: "total" } satisfies Record<ClientSortKey, keyof typeof salesClients[number]>;
    return [...filtered]
      .sort((left, right) => sortDir === "asc" ? Number(left[key[sortKey]]) - Number(right[key[sortKey]]) : Number(right[key[sortKey]]) - Number(left[key[sortKey]]))
      .map(toSalesClientRow);
  }, [buyerOnly, channelFilter, openOnly, productFilter, query, sortDir, sortKey]);

  function setQuery(value: string) {
    setQueryState(value);
    setMenu(null);
  }

  function toggleProduct(code: string) {
    setProductFilter((current) => current.includes(code as ClientProductCode) ? current.filter((item) => item !== code) : [...current, code as ClientProductCode]);
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
    setProductFilter([]);
    setChannelFilter([]);
    setOpenOnly(false);
    setBuyerOnly(false);
    setMenu(null);
    setDropdown(null);
  }

  return {
    rows,
    query,
    productFilter,
    channelFilter,
    openOnly,
    buyerOnly,
    dropdown,
    menu,
    setMenu,
    setQuery,
    toggleProduct,
    toggleChannel,
    toggleDropdown,
    closeDropdown: () => setDropdown(null),
    toggleOpenOnly: () => { setOpenOnly((current) => !current); setMenu(null); setDropdown(null); },
    toggleBuyerOnly: () => { setBuyerOnly((current) => !current); setMenu(null); setDropdown(null); },
    sortBy,
    sortArrow: (key: ClientSortKey) => sortKey === key ? (sortDir === "asc" ? "↑" : "↓") : "",
    reset,
  };
}

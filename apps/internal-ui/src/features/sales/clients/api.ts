import { api } from "../../../api/client";
import type { PagedPayload } from "../../../shared/usePagedResource";
import type { ApiClient, ClientChannelCode, ClientSortKey } from "./model";

// Список контактов (кадры K1/K2): страницу, фильтры, поиск и порядок считает
// сервер — контактов у работающей организации столько же, сколько клиентов.

export type ClientsQuery = {
  query: string;
  agentFilter: number[];
  channelFilter: ClientChannelCode[];
  openOnly: boolean;
  sortKey: ClientSortKey;
  sortDir: "asc" | "desc";
};

// Выгрузка CSV идёт теми же фильтрами, но крупными страницами; потолок в
// 10 000 строк защищает браузер от выгрузки всей базы одним файлом.
const EXPORT_PAGE_SIZE = 100;
const EXPORT_PAGE_LIMIT = 100;

function searchParams({ query, agentFilter, channelFilter, openOnly, sortKey, sortDir }: ClientsQuery): URLSearchParams {
  const params = new URLSearchParams();
  if (query.trim()) params.set("q", query.trim());
  for (const agent of agentFilter) params.append("agent", String(agent));
  for (const channel of channelFilter) params.append("channel", channel);
  if (openOnly) params.set("open", "1");
  params.set("sort", sortKey === "open" ? "open" : "last");
  params.set("dir", sortDir);
  return params;
}

export function fetchClients(query: ClientsQuery, page: number): Promise<PagedPayload<ApiClient>> {
  const params = searchParams(query);
  params.set("page", String(page));
  return api<PagedPayload<ApiClient>>(`/api/v1/conversations/clients/?${params.toString()}`);
}

/** Все строки под текущими фильтрами — для выгрузки в CSV. */
export async function fetchClientsForExport(query: ClientsQuery): Promise<ApiClient[]> {
  const rows: ApiClient[] = [];
  for (let page = 1; page <= EXPORT_PAGE_LIMIT; page += 1) {
    const params = searchParams(query);
    params.set("page", String(page));
    params.set("pageSize", String(EXPORT_PAGE_SIZE));
    const payload = await api<PagedPayload<ApiClient>>(
      `/api/v1/conversations/clients/?${params.toString()}`,
    );
    rows.push(...payload.items);
    if (payload.page >= payload.pageCount) break;
  }
  return rows;
}

/** Сколько контактов всего — для счётчика «6 из 128» в шапке. Берётся одна
 *  строка: нужен только total. */
export function fetchClientsTotal(): Promise<number> {
  return api<PagedPayload<ApiClient>>("/api/v1/conversations/clients/?pageSize=1").then((page) => page.total);
}

import { Icon } from "../../../shared/icons";
import { SalesClientRow } from "./SalesClientRow";
import { Pagination } from "../../../shared/Pagination";
import type { SalesClientsState } from "./useSalesClients";

// Таблица контактов (кадр K1): шапка · строки 60px · подвал со страницами.
// Колонки: Контакт · Как связаться · Каналы · Последний диалог · Открытые · ⋯

export function SalesClientsTable({ clients, openClient }: { clients: SalesClientsState; openClient: (id: number) => void }) {
  const from = (clients.page - 1) * clients.pageSize + 1;
  const to = from + clients.rows.length - 1;
  const shown = clients.total === 0 ? "Ничего не найдено" : `${from}–${to} из ${clients.total}`;
  return (
    <div className="sales-clients-card">
      <div className="sales-clients-head">
        <span>Контакт</span>
        <span>Как связаться</span>
        <span>Каналы</span>
        <button className={clients.sortKey === "last" ? "is-active" : ""} type="button" onClick={() => clients.sortBy("last")}>
          Последний диалог
          <i className={`sales-clients-sort ${clients.sortKey === "last" && clients.sortDir === "desc" ? "is-up" : ""}`}><Icon name="arrowDown" size={11} strokeWidth={2.5} /></i>
        </button>
        <button className={`is-numeric ${clients.sortKey === "open" ? "is-active" : ""}`} type="button" onClick={() => clients.sortBy("open")}>
          Открытые
          {clients.sortKey === "open" && <i className={`sales-clients-sort ${clients.sortDir === "desc" ? "is-up" : ""}`}><Icon name="arrowDown" size={11} strokeWidth={2.5} /></i>}
        </button>
        <span />
      </div>
      {clients.rows.map((client) => (
        <SalesClientRow client={client} menu={clients.menu} openClient={openClient} setMenu={clients.setMenu} key={client.cid} />
      ))}
      {clients.rows.length === 0 && (
        <div className="sales-clients-empty">
          <Icon name="search" size={20} />
          <strong>Контакты не найдены</strong>
          <span>Измените условия фильтра или сбросьте их.</span>
        </div>
      )}
      <Pagination
        className="sales-clients-foot"
        note={shown}
        page={clients.page}
        pageCount={clients.pageCount}
        onPage={clients.setPage}
      />
    </div>
  );
}

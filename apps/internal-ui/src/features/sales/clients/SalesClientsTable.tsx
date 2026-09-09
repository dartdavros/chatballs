import { Icon } from "../../../shared/icons";
import { SalesClientRow } from "./SalesClientRow";
import { Pagination } from "../../../shared/Pagination";
import type { SalesClientsState } from "./useSalesClients";
import { t } from "../../../i18n";

// Таблица контактов (кадр K1): шапка · строки 60px · подвал со страницами.
// Колонки: Контакт · Как связаться · Каналы · Последний диалог · Открытые · ⋯

export function SalesClientsTable({ clients, openClient }: { clients: SalesClientsState; openClient: (id: number) => void }) {
  const from = (clients.page - 1) * clients.pageSize + 1;
  const to = from + clients.rows.length - 1;
  const shown = clients.total === 0 ? t("common.nothing_found") : t("common.range_of", { from, to, total: clients.total });
  return (
    <div className="sales-clients-card">
      <div className="sales-clients-head">
        <span>{t("common.contact")}</span>
        <span>{t("sales.how_reach_them")}</span>
        <span>{t("common.channels")}</span>
        <button className={clients.sortKey === "last" ? "is-active" : ""} type="button" onClick={() => clients.sortBy("last")}>{t("sales.last_conversation")}<i className={`sales-clients-sort ${clients.sortKey === "last" && clients.sortDir === "desc" ? "is-up" : ""}`}><Icon name="arrowDown" size={11} strokeWidth={2.5} /></i>
        </button>
        <button className={`is-numeric ${clients.sortKey === "open" ? "is-active" : ""}`} type="button" onClick={() => clients.sortBy("open")}>
          {t("sales.open_column")}
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
          <strong>{t("sales.no_contacts_found")}</strong>
          <span>{t("sales.change_filter_conditions_or_clear")}</span>
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

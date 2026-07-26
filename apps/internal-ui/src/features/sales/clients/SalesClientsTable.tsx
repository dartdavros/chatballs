import { Icon } from "../../../shared/icons";
import { SalesClientRow } from "./SalesClientRow";
import { SalesClientsPagination } from "./SalesClientsPagination";
import type { ClientSortKey } from "./model";
import type { SalesClientsState } from "./useSalesClients";

export function SalesClientsTable({ clients, openClient }: { clients: SalesClientsState; openClient: (id: number) => void }) {
  return (
    <>
      <div className="sales-clients-card">
        <div className="sales-clients-table-scroll">
          <table className="sales-clients-table">
            <thead>
              <tr>
                <th>КОНТАКТ</th>
                <th>СТАТУС</th>
                <th>ТЕЛЕФОН / EMAIL / ЛОГИН</th>
                <th>КАНАЛЫ</th>
                <th>ПРОДУКТЫ</th>
                <SortableTh label="ПОСЛ. ДИАЛОГ" sortKey="last" clients={clients} />
                <SortableTh label="ОТКР." sortKey="open" clients={clients} numeric />
                <SortableTh label="ЗАКАЗЫ" sortKey="orders" clients={clients} numeric />
                <SortableTh label="СУММА ПОКУПОК" sortKey="total" clients={clients} numeric />
                <th />
              </tr>
            </thead>
            <tbody>
              {clients.rows.map((client) => <SalesClientRow client={client} menu={clients.menu} openClient={openClient} setMenu={clients.setMenu} key={client.cid} />)}
            </tbody>
          </table>
        </div>
        {clients.rows.length === 0 && <SalesClientsEmpty />}
        <SalesClientsPagination page={clients.page} pageCount={clients.pageCount} shownCount={clients.rows.length} totalCount={clients.filteredCount} setPage={clients.setPage} />
      </div>
    </>
  );
}

function SortableTh({ label, sortKey, clients, numeric = false }: { label: string; sortKey: ClientSortKey; clients: SalesClientsState; numeric?: boolean }) {
  return (
    <th className={numeric ? "numeric" : ""}>
      <button type="button" onClick={() => clients.sortBy(sortKey)}>{label} {clients.sortArrow(sortKey)}</button>
    </th>
  );
}

function SalesClientsEmpty() {
  return (
    <div className="sales-clients-empty">
      <div><Icon name="search" size={22} /></div>
      <strong>Контакты не найдены</strong>
      <span>Измените условия фильтра или сбросьте их.</span>
    </div>
  );
}

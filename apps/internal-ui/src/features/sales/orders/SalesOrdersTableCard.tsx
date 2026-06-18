import { Icon } from "../../../shared/icons";
import { FulfillmentTable } from "./tables/FulfillmentTable";
import { OrdersTable } from "./tables/OrdersTable";
import { PaymentsTable } from "./tables/PaymentsTable";
import { RefundsTable } from "./tables/RefundsTable";
import { SubscriptionsTable } from "./tables/SubscriptionsTable";
import type { SalesFulfillment, SalesOrder, SalesOrdersTab, SalesPayment, SalesRefund, SalesSubscription } from "./types";

export function SalesOrdersTableCard({ activeTab, rows }: { activeTab: SalesOrdersTab; rows: Array<{ search: string }> }) {
  return (
    <div className="sales-orders-card">
      <div className="sales-orders-table-scroll">
        {activeTab === "orders" && <OrdersTable rows={rows as SalesOrder[]} />}
        {activeTab === "subs" && <SubscriptionsTable rows={rows as SalesSubscription[]} />}
        {activeTab === "pays" && <PaymentsTable rows={rows as SalesPayment[]} />}
        {activeTab === "refunds" && <RefundsTable rows={rows as SalesRefund[]} />}
        {activeTab === "exec" && <FulfillmentTable rows={rows as SalesFulfillment[]} />}
        {rows.length === 0 && <SalesOrdersEmpty />}
      </div>
    </div>
  );
}

function SalesOrdersEmpty() {
  return (
    <div className="sales-orders-empty">
      <div><Icon name="search" size={22} /></div>
      <strong>Ничего не найдено</strong>
      <span>Измените поисковый запрос.</span>
    </div>
  );
}

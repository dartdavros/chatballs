import { SalesActorsCard } from "./SalesActorsCard";
import { SalesChannelsCard } from "./SalesChannelsCard";
import { SalesListCard } from "./SalesListCard";
import { SalesProductsTable } from "./SalesProductsTable";
import type { SalesOverviewVm } from "./model";

export function SalesOverviewGrid({ vm }: { vm: SalesOverviewVm }) {
  return (
    <div className="sales-overview-grid">
      <SalesProductsTable products={vm.products} />
      <SalesChannelsCard channels={vm.channels} />
      <SalesActorsCard vm={vm} />
      <SalesListCard title="Проблемные диалоги" icon="warning" items={vm.problems} />
      <SalesListCard title="Платежи и fulfillment" icon="box" items={vm.payments} />
    </div>
  );
}

import { SalesActorsCard } from "./SalesActorsCard";
import { SalesChannelsCard } from "./SalesChannelsCard";
import { SalesListCard } from "./SalesListCard";
import { SalesProductsTable } from "./SalesProductsTable";
import type { SalesOverviewVm } from "./model";

export function SalesOverviewGrid({ vm, openConversation }: { vm: SalesOverviewVm; openConversation: (conversationId: number) => void }) {
  return (
    <div className="sales-overview-grid">
      <SalesProductsTable products={vm.products} />
      <SalesChannelsCard channels={vm.channels} />
      <SalesActorsCard vm={vm} />
      <SalesListCard title="Проблемные диалоги" items={vm.problems} openConversation={openConversation} />
    </div>
  );
}

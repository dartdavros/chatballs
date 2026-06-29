import { ClientContext } from "./context/ClientContext";
import { HistoryContext } from "./context/HistoryContext";
import { ProductContext } from "./context/ProductContext";
import { SalesContextTabs } from "./context/SalesContextTabs";
import type { ApiConversation } from "./model";
import type { RightTab, SalesDialog } from "./types";

export function SalesContextPanel({ rightTab, setRightTab, dialog, detail }: { rightTab: RightTab; setRightTab: (tab: RightTab) => void; dialog: SalesDialog | null; detail: ApiConversation | null }) {
  return (
    <section className="sales-context">
      <SalesContextTabs rightTab={rightTab} setRightTab={setRightTab} />
      <div className="sales-context-body">
        {rightTab === "client" && <ClientContext dialog={dialog} detail={detail} />}
        {rightTab === "product" && <ProductContext detail={detail} />}
        {rightTab === "history" && <HistoryContext detail={detail} />}
      </div>
    </section>
  );
}

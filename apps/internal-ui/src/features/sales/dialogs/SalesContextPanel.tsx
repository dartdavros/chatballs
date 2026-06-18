import { ClientContext } from "./context/ClientContext";
import { HistoryContext } from "./context/HistoryContext";
import { ProductContext } from "./context/ProductContext";
import { SalesContextTabs } from "./context/SalesContextTabs";
import type { RightTab } from "./types";

export function SalesContextPanel({ rightTab, setRightTab }: { rightTab: RightTab; setRightTab: (tab: RightTab) => void }) {
  return (
    <section className="sales-context">
      <SalesContextTabs rightTab={rightTab} setRightTab={setRightTab} />
      <div className="sales-context-body">
        {rightTab === "client" && <ClientContext />}
        {rightTab === "product" && <ProductContext />}
        {rightTab === "history" && <HistoryContext />}
      </div>
    </section>
  );
}

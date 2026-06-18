import type { ReactNode } from "react";

import type { RightTab } from "../types";

export function SalesContextTabs({ rightTab, setRightTab }: { rightTab: RightTab; setRightTab: (tab: RightTab) => void }) {
  return (
    <div className="sales-context-tabs">
      <RightTabButton active={rightTab === "client"} onClick={() => setRightTab("client")}>Клиент</RightTabButton>
      <RightTabButton active={rightTab === "product"} onClick={() => setRightTab("product")}>Продукт</RightTabButton>
      <RightTabButton active={rightTab === "history"} onClick={() => setRightTab("history")}>История</RightTabButton>
    </div>
  );
}

function RightTabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return <button className={active ? "active" : ""} onClick={onClick}>{children}</button>;
}

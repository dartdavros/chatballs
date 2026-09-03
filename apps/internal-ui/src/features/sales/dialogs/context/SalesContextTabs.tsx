import type { ReactNode } from "react";

export type SalesRightTab = "client" | "history";

export function SalesContextTabs({ rightTab, setRightTab }: { rightTab: SalesRightTab; setRightTab: (tab: SalesRightTab) => void }) {
  return (
    <div className="sales-context-tabs">
      <RightTabButton active={rightTab === "client"} onClick={() => setRightTab("client")}>Контакт</RightTabButton>
      <RightTabButton active={rightTab === "history"} onClick={() => setRightTab("history")}>История</RightTabButton>
    </div>
  );
}

function RightTabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return <button className={active ? "active" : ""} onClick={onClick}>{children}</button>;
}

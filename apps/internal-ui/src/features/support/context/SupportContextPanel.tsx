import type { ReactNode } from "react";

import type { ApiConversation } from "../../conversations/model";
import { OperatorCards } from "./OperatorCards";
import { SupportHistory } from "./SupportHistory";

export type SupportRightTab = "client" | "history";

export function SupportContextPanel({ rightTab, setRightTab, detail }: { rightTab: SupportRightTab; setRightTab: (tab: SupportRightTab) => void; detail: ApiConversation | null }) {
  return (
    <section className="sales-context">
      <div className="sales-context-tabs">
        <RightTabButton active={rightTab === "client"} onClick={() => setRightTab("client")}>Контакт</RightTabButton>
        <RightTabButton active={rightTab === "history"} onClick={() => setRightTab("history")}>История</RightTabButton>
      </div>
      <div className="sales-context-body">
        {rightTab === "client" && <OperatorCards detail={detail} />}
        {rightTab === "history" && <SupportHistory detail={detail} />}
      </div>
    </section>
  );
}

function RightTabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return <button className={active ? "active" : ""} onClick={onClick}>{children}</button>;
}

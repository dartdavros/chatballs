import type { ReactNode } from "react";

import type { ApiConversation } from "../../conversations/model";
import { DialogControls } from "../../conversations/DialogControls";
import { OperatorCards } from "./OperatorCards";
import { SupportHistory } from "./SupportHistory";
import type { EmployeeGroupRef } from "../../../types";

export type SupportRightTab = "client" | "history";

export function SupportContextPanel({ rightTab, setRightTab, detail, groups = [], employees = [], applyConversation }: { rightTab: SupportRightTab; setRightTab: (tab: SupportRightTab) => void; detail: ApiConversation | null; groups?: EmployeeGroupRef[]; employees?: Array<{ id: number; name: string }>; applyConversation?: (updated: ApiConversation) => void }) {
  return (
    <section className="sales-context">
      <div className="sales-context-tabs">
        <RightTabButton active={rightTab === "client"} onClick={() => setRightTab("client")}>Контакт</RightTabButton>
        <RightTabButton active={rightTab === "history"} onClick={() => setRightTab("history")}>История</RightTabButton>
      </div>
      <div className="sales-context-body">
        {rightTab === "client" && (
          <>
            {detail && applyConversation && (
              <DialogControls detail={detail} groups={groups} employees={employees} applyConversation={applyConversation} />
            )}
            <OperatorCards detail={detail} />
          </>
        )}
        {rightTab === "history" && <SupportHistory detail={detail} />}
      </div>
    </section>
  );
}

function RightTabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return <button className={active ? "active" : ""} onClick={onClick}>{children}</button>;
}

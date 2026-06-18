import { useMemo, useState } from "react";

import { SalesComposer } from "./dialogs/SalesComposer";
import { SalesContextPanel } from "./dialogs/SalesContextPanel";
import { SalesConversation } from "./dialogs/SalesConversation";
import { SalesDialogList } from "./dialogs/SalesDialogList";
import { dialogs } from "./dialogs/data";
import type { ControlMode, ListTab, RightTab } from "./dialogs/types";

export function SalesDialogsPage() {
  const [listTab, setListTab] = useState<ListTab>("all");
  const [rightTab, setRightTab] = useState<RightTab>("client");
  const [selectedId, setSelectedId] = useState(1);
  const [controlMode, setControlMode] = useState<ControlMode>("waiting");

  const selected = dialogs.find((dialog) => dialog.id === selectedId) ?? dialogs[0];
  const filtered = useMemo(() => dialogs.filter((dialog) => {
    if (listTab === "wait") return dialog.mode === "wait";
    if (listTab === "ai") return dialog.mode === "ai";
    if (listTab === "operator") return dialog.mode === "operator";
    if (listTab === "unread") return dialog.unread > 0;
    return true;
  }), [listTab]);

  return (
    <div className="sales-dialogs">
      <SalesDialogList
        dialogs={dialogs}
        filtered={filtered}
        listTab={listTab}
        selectedId={selectedId}
        setListTab={setListTab}
        setSelectedId={setSelectedId}
      />
      <section className="sales-conversation">
        <SalesConversation controlMode={controlMode} selected={selected} setControlMode={setControlMode} />
        <SalesComposer mode={controlMode} setMode={setControlMode} />
      </section>
      <SalesContextPanel rightTab={rightTab} setRightTab={setRightTab} />
    </div>
  );
}

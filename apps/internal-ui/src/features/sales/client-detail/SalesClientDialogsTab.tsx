import { EmptyState } from "../../../shared/ui";
import type { RouteKey } from "../../../types";
import type { ClientDetailVm } from "./model";

export function SalesClientDialogsTab({ dialogs, setRoute }: { dialogs: ClientDetailVm["dialogs"]; setRoute: (route: RouteKey) => void }) {
  if (dialogs.length === 0) return <EmptyState title="У клиента ещё нет диалогов" />;
  return (
    <div className="sales-client-list-card">
      {dialogs.map((dialog) => (
        <button className="sales-client-dialog-link" type="button" onClick={() => setRoute("salesDialogs")} key={dialog.id}>
          <span className="sales-client-dialog-dot" style={{ background: dialog.active ? "#1677ff" : "#bfbfbf" }} />
          <span className="sales-client-dialog-copy"><strong>{dialog.title}</strong><small>{dialog.meta}</small></span>
          <b className={dialog.active ? "active" : ""}>{dialog.status}</b>
          <time>{dialog.time}</time>
        </button>
      ))}
    </div>
  );
}

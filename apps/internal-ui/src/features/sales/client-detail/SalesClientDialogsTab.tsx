import type { RouteKey } from "../../../types";
import type { salesClientDetail } from "./model";

type Dialog = typeof salesClientDetail.dialogs[number];

export function SalesClientDialogsTab({ dialogs, setRoute }: { dialogs: Dialog[]; setRoute: (route: RouteKey) => void }) {
  return (
    <div className="sales-client-list-card">
      {dialogs.map((dialog) => (
        <button className="sales-client-dialog-link" type="button" onClick={() => setRoute("salesDialogs")} key={dialog.title}>
          <span className="sales-client-dialog-dot" style={{ background: dialog.active ? "#1677ff" : "#bfbfbf" }} />
          <span className="sales-client-dialog-copy"><strong>{dialog.title}</strong><small>{dialog.meta}</small></span>
          <b className={dialog.active ? "active" : ""}>{dialog.status}</b>
          <time>{dialog.time}</time>
        </button>
      ))}
    </div>
  );
}

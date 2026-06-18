import type { ReactNode } from "react";
import type { ListTab, SalesDialog } from "./types";
import { channelMeta, modeDots } from "./data";
import { Icon } from "../../../shared/icons";

export function SalesDialogList({ dialogs, filtered, listTab, selectedId, setListTab, setSelectedId }: {
  dialogs: SalesDialog[];
  filtered: SalesDialog[];
  listTab: ListTab;
  selectedId: number;
  setListTab: (tab: ListTab) => void;
  setSelectedId: (id: number) => void;
}) {
  return (
    <section className="sales-dialog-list">
      <div className="sales-dialog-list-head">
        <div><h2>Диалоги</h2><span>{dialogs.length} всего</span></div>
        <label className="sales-dialog-search"><Icon name="search" size={15} /><input placeholder="Поиск по клиенту, продукту…" /></label>
      </div>
      <div className="sales-dialog-tabs">
        <DialogTab active={listTab === "all"} onClick={() => setListTab("all")}>Все</DialogTab>
        <DialogTab active={listTab === "wait"} onClick={() => setListTab("wait")}>Ждут оператора <b>2</b></DialogTab>
        <DialogTab active={listTab === "ai"} onClick={() => setListTab("ai")}>AI</DialogTab>
        <DialogTab active={listTab === "operator"} onClick={() => setListTab("operator")}>Оператор</DialogTab>
        <DialogTab active={listTab === "unread"} onClick={() => setListTab("unread")}>Непрочитанные</DialogTab>
      </div>
      <div className="sales-dialog-list-body">
        {filtered.map((dialog) => <DialogListItem dialog={dialog} active={dialog.id === selectedId} setSelectedId={setSelectedId} key={dialog.id} />)}
      </div>
    </section>
  );
}

function DialogTab({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return <button className={active ? "active" : ""} onClick={onClick}>{children}</button>;
}

function DialogListItem({ dialog, active, setSelectedId }: { dialog: SalesDialog; active: boolean; setSelectedId: (id: number) => void }) {
  const channel = channelMeta[dialog.channel];
  return (
    <button className={`sales-dialog-row ${active ? "active" : ""}`} onClick={() => setSelectedId(dialog.id)}>
      <span className="sales-dialog-row-bar" />
      <span className="sales-dialog-avatar-wrap">
        <span className="sales-dialog-avatar" style={{ background: dialog.avatarBg }}>{dialog.initials}</span>
        <i style={{ background: modeDots[dialog.mode] }} />
      </span>
      <span className="sales-dialog-row-main">
        <span className="sales-dialog-row-title"><strong>{dialog.name}</strong><em>{dialog.time}</em></span>
        <span className="sales-dialog-row-meta"><small>{dialog.product}</small><b style={{ background: channel.bg, color: channel.color }}><i style={{ background: channel.color }} />{channel.label}</b></span>
        <span className="sales-dialog-row-preview"><small className={dialog.unread ? "unread" : ""}>{dialog.preview}</small>{dialog.unread > 0 && <b>{dialog.unread}</b>}</span>
      </span>
    </button>
  );
}

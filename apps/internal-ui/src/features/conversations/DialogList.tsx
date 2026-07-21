import type { ReactNode } from "react";

import { modeDots } from "./data";
import { providerMeta } from "../../shared/providers";
import type { ConversationListItem, ListTab } from "./types";
import { SearchInput } from "../../shared/ui-controls";

export function DialogList({ title = "Диалоги", searchPlaceholder = "Поиск по клиенту, продукту…", dialogs, filtered, listTab, selectedId, search, setSearch, setListTab, setSelectedId }: {
  title?: string;
  searchPlaceholder?: string;
  dialogs: ConversationListItem[];
  filtered: ConversationListItem[];
  listTab: ListTab;
  selectedId: number;
  search: string;
  setSearch: (value: string) => void;
  setListTab: (tab: ListTab) => void;
  setSelectedId: (id: number) => void;
}) {
  const waitCount = dialogs.filter((dialog) => dialog.mode === "wait").length;
  const unreadCount = dialogs.filter((dialog) => dialog.unread > 0).length;
  return (
    <section className="sales-dialog-list">
      <div className="sales-dialog-list-head">
        <div><h2>{title}</h2><span>{dialogs.length} всего</span></div>
        <SearchInput className="sales-dialog-search" placeholder={searchPlaceholder} value={search} onChange={setSearch} />
      </div>
      <div className="sales-dialog-tabs">
        <DialogTab active={listTab === "all"} onClick={() => setListTab("all")}>Все</DialogTab>
        <DialogTab active={listTab === "wait"} onClick={() => setListTab("wait")}>Ждут оператора {waitCount > 0 && <b>{waitCount}</b>}</DialogTab>
        <DialogTab active={listTab === "ai"} onClick={() => setListTab("ai")}>AI</DialogTab>
        <DialogTab active={listTab === "operator"} onClick={() => setListTab("operator")}>Оператор</DialogTab>
        <DialogTab active={listTab === "unread"} onClick={() => setListTab("unread")}>Непрочитанные {unreadCount > 0 && <b>{unreadCount}</b>}</DialogTab>
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

function DialogListItem({ dialog, active, setSelectedId }: { dialog: ConversationListItem; active: boolean; setSelectedId: (id: number) => void }) {
  const channel = providerMeta[dialog.channel];
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

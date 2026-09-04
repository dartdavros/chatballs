import type { ReactNode } from "react";

import { modeDots } from "./data";
import { ContactAvatar } from "./ContactAvatar";
import { providerMeta } from "../../shared/providers";
import type { ConversationListItem, ListTab } from "./types";
import { SearchInput } from "../../shared/ui-controls";

export function DialogList({ title = "Диалоги", searchPlaceholder = "Поиск по клиенту, продукту…", dialogs, filtered, listTab, selectedId, search, errorText, setSearch, setListTab, setSelectedId }: {
  title?: string;
  searchPlaceholder?: string;
  dialogs: ConversationListItem[];
  filtered: ConversationListItem[];
  listTab: ListTab;
  selectedId: number;
  search: string;
  errorText?: string;
  setSearch: (value: string) => void;
  setListTab: (tab: ListTab) => void;
  setSelectedId: (id: number) => void;
}) {
  const waitCount = dialogs.filter((dialog) => dialog.mode === "wait").length;
  return (
    <section className="sales-dialog-list">
      <div className="sales-dialog-list-head">
        <div><h2>{title}</h2><span>{dialogs.length} всего</span></div>
        <SearchInput className="sales-dialog-search" placeholder={searchPlaceholder} value={search} onChange={setSearch} />
      </div>
      <div className="sales-dialog-tabs">
        <DialogTab active={listTab === "all"} onClick={() => setListTab("all")}>Все</DialogTab>
        <DialogTab active={listTab === "mine"} onClick={() => setListTab("mine")}>Мои</DialogTab>
        <DialogTab active={listTab === "wait"} onClick={() => setListTab("wait")}>Ждут оператора {waitCount > 0 && <b>{waitCount}</b>}</DialogTab>
      </div>
      <div className="sales-dialog-list-body">
        {errorText && <div className="sales-wait-note sales-load-error">{errorText}</div>}
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
        <ContactAvatar avatarUrl={dialog.avatarUrl} initials={dialog.initials} background={dialog.avatarBg} className="sales-dialog-avatar" />
        <i style={{ background: modeDots[dialog.mode] }} />
      </span>
      <span className="sales-dialog-row-main">
        <span className="sales-dialog-row-title"><strong>{dialog.name}</strong><em>{dialog.time}</em></span>
        <span className="sales-dialog-row-meta"><small>{dialog.product}</small><b style={{ background: channel.bg, color: channel.color }}><i style={{ background: channel.color }} />{channel.label}</b></span>
        <span className="sales-dialog-row-preview"><small className={dialog.unread ? "unread" : ""}>{dialog.preview}</small>{dialog.unread > 0 && <b>{dialog.unread}</b>}</span>
        {(dialog.priority !== "NONE" || dialog.labels.length > 0) && (
          <span className="sales-dialog-row-badges">
            {dialog.priority !== "NONE" && <PriorityBars priority={dialog.priority} />}
            {dialog.labels.map((label) => (
              <b className="sales-dialog-label" key={label.id}><i style={{ background: label.color || "var(--n-5)" }} />{label.name}</b>
            ))}
          </span>
        )}
      </span>
    </button>
  );
}

const PRIORITY_TITLE: Record<string, string> = { HIGH: "Высокий", MEDIUM: "Средний", LOW: "Низкий" };
const PRIORITY_ON: Record<string, number> = { HIGH: 3, MEDIUM: 2, LOW: 1 };
const PRIORITY_COLOR: Record<string, string> = { HIGH: "#ff4d4f", MEDIUM: "#fa8c16", LOW: "#1677ff" };

export function PriorityBars({ priority }: { priority: "HIGH" | "MEDIUM" | "LOW" | "NONE" }) {
  if (priority === "NONE") return null;
  const on = PRIORITY_ON[priority] ?? 0;
  const color = PRIORITY_COLOR[priority];
  return (
    <span className="sales-priority-bars" title={PRIORITY_TITLE[priority]}>
      {[5, 8, 11].map((height, index) => (
        <i key={height} style={{ height, background: index < on ? color : "var(--n-7)" }} />
      ))}
    </span>
  );
}

import { Dropdown } from "antd";
import type { ReactNode } from "react";

import { modeDots } from "./data";
import { ContactAvatar } from "./ContactAvatar";
import { Icon } from "../../shared/icons";
import { providerMeta } from "../../shared/providers";
import { scopeLabel, type DialogScope } from "./ConversationWorkspace";
import type { ConversationCounters } from "./model";
import type { ConversationListItem, ListTab } from "./types";
import { SearchInput } from "../../shared/ui-controls";

export function DialogList({ title = "Диалоги", searchPlaceholder = "Поиск по клиенту, продукту…", scope, counters, setScope, dialogs, filtered, listTab, selectedId, search, errorText, setSearch, setListTab, setSelectedId }: {
  title?: string;
  searchPlaceholder?: string;
  scope: DialogScope;
  counters: ConversationCounters | null;
  setScope: (scope: DialogScope) => void;
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
        <div>
          <ScopeSwitcher scope={scope} counters={counters} setScope={setScope} fallbackTitle={title} />
          <span>{dialogs.length} всего</span>
        </div>
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

// Переключатель охвата (дизайн-базлайн v2 A1): Все диалоги · Группы · Агенты.
// Дерево фильтров живёт в заголовке списка, сайдбар остаётся плоским.
function ScopeSwitcher({ scope, counters, setScope, fallbackTitle }: { scope: DialogScope; counters: ConversationCounters | null; setScope: (scope: DialogScope) => void; fallbackTitle: string }) {
  if (!counters || (counters.groups.length === 0 && counters.agents.length <= 1)) {
    return <h2>{scope.kind === "all" ? fallbackTitle : scopeLabel(scope)}</h2>;
  }
  const items = [
    {
      key: "all",
      label: <button type="button" onClick={() => setScope({ kind: "all" })}><Icon name="box" size={15} />Все диалоги<small>{counters.all}</small></button>,
    },
    ...(counters.groups.length > 0
      ? [
          { key: "groups-head", type: "group" as const, label: "ГРУППЫ" },
          ...counters.groups.map((group) => ({
            key: `group-${group.id}`,
            label: (
              <button type="button" onClick={() => setScope({ kind: "group", id: group.id, label: group.name })}>
                <i className="scope-dot" />{group.name}<small>{group.count}</small>
              </button>
            ),
          })),
          {
            key: "ungrouped",
            label: <button type="button" onClick={() => setScope({ kind: "ungrouped" })}><i className="scope-dot is-muted" />Без группы<small>{counters.ungrouped}</small></button>,
          },
        ]
      : []),
    ...(counters.agents.length > 0
      ? [
          { key: "agents-head", type: "group" as const, label: "АГЕНТЫ" },
          ...counters.agents.map((agent) => ({
            key: `agent-${agent.id}`,
            label: (
              <button type="button" onClick={() => setScope({ kind: "agent", id: agent.id, label: agent.name })}>
                <Icon name="robot" size={14} />{agent.name}<small>{agent.count}</small>
              </button>
            ),
          })),
        ]
      : []),
  ];
  return (
    <Dropdown menu={{ items }} trigger={["click"]} placement="bottomLeft" overlayClassName="app-dropdown scope-dropdown">
      <button className="sales-scope-switcher" type="button">
        <h2>{scope.kind === "all" ? fallbackTitle : scopeLabel(scope)}</h2>
        <Icon name="chevron" size={14} />
      </button>
    </Dropdown>
  );
}

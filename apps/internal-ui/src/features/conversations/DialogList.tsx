import { Dropdown } from "antd";
import type { ReactNode, RefObject } from "react";

import { modeDots } from "./data";
import { ContactAvatar } from "./ContactAvatar";
import { Icon } from "../../shared/icons";
import { ChannelGlyph } from "../../shared/badges";
import { scopeLabel, type DialogScope } from "./ConversationWorkspace";
import type { ConversationCounters } from "./model";
import type { ConversationListItem, ListTab } from "./types";
import { SearchInput } from "../../shared/ui-controls";

export type ListSort = "activity" | "waiting";

export function DialogList({ title = "Диалоги", searchPlaceholder = "Поиск по контакту, сообщению…", scope, counters, setScope, showScopeSwitcher = true, mobileHeader, hint, searchRef, dialogs, filtered, listTab, selectedId, search, errorText, sort, setSort, onCollapse, setSearch, setListTab, setSelectedId }: {
  title?: string;
  searchPlaceholder?: string;
  sort: ListSort;
  setSort: (sort: ListSort) => void;
  onCollapse?: () => void;
  scope: DialogScope;
  counters: ConversationCounters | null;
  setScope: (scope: DialogScope) => void;
  showScopeSwitcher?: boolean;
  mobileHeader?: (info: { total: number }) => ReactNode;
  hint?: ReactNode;
  searchRef?: RefObject<HTMLInputElement | null>;
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
      {mobileHeader?.({ total: dialogs.length })}
      <div className="sales-dialog-list-head">
        <div>
          {showScopeSwitcher
            ? <ScopeSwitcher scope={scope} counters={counters} setScope={setScope} fallbackTitle={title} total={dialogs.length} />
            : <h2 className="sales-dialog-list-title">{scope.kind === "all" ? title : scopeLabel(scope)}<small>{dialogs.length}</small></h2>}
          <span className="sales-dialog-list-tools">
            <Dropdown
              trigger={["click"]}
              placement="bottomRight"
              overlayClassName="app-dropdown"
              menu={{
                items: [
                  { key: "activity", label: <button type="button" className={sort === "activity" ? "is-checked" : ""} onClick={() => setSort("activity")}>По последнему сообщению</button> },
                  { key: "waiting", label: <button type="button" className={sort === "waiting" ? "is-checked" : ""} onClick={() => setSort("waiting")}>По времени ожидания</button> },
                ],
              }}
            >
              <button type="button" aria-label="Сортировка" title={sort === "activity" ? "Сортировка: по последнему сообщению" : "Сортировка: по времени ожидания"}><Icon name="sort" size={15} /></button>
            </Dropdown>
            {onCollapse && <button type="button" aria-label="Скрыть список" title="Скрыть список" onClick={onCollapse}><Icon name="collapseLeft" size={15} /></button>}
          </span>
        </div>
        <SearchInput className="sales-dialog-search" inputRef={searchRef} placeholder={searchPlaceholder} value={search} onChange={setSearch} hotkey="/" />
      </div>
      <div className="sales-dialog-tabs">
        <DialogTab active={listTab === "all"} onClick={() => setListTab("all")}>Все</DialogTab>
        <DialogTab active={listTab === "mine"} onClick={() => setListTab("mine")}>Мои</DialogTab>
        <DialogTab active={listTab === "wait"} onClick={() => setListTab("wait")}>Ждут оператора{waitCount > 0 && <b>{waitCount}</b>}</DialogTab>
      </div>
      {hint}
      <div className="sales-dialog-list-body">
        {errorText && <div className="sales-wait-note sales-load-error">{errorText}</div>}
        {/* Кадр S1: пустой список без призыва к действию. */}
        {!errorText && dialogs.length === 0 && (
          <div className="sales-dialog-list-empty"><span><Icon name="message" size={20} /></span><p>Диалоги появятся, когда клиенты напишут вашему агенту</p></div>
        )}
        {filtered.map((dialog) => <DialogListItem dialog={dialog} active={dialog.id === selectedId} setSelectedId={setSelectedId} key={dialog.id} />)}
      </div>
    </section>
  );
}

function DialogTab({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return <button className={active ? "active" : ""} onClick={onClick}>{children}</button>;
}

function DialogListItem({ dialog, active, setSelectedId }: { dialog: ConversationListItem; active: boolean; setSelectedId: (id: number) => void }) {
  // Строка по дизайн-базлайну v2 (решение 4): канал + агент → имя · время →
  // превью (↩ если последнее сообщение наше) · непрочитанные → таймер ожидания,
  // группа, метки. Точка на аватаре — режим диалога.
  return (
    <button className={`sales-dialog-row ${active ? "active" : ""}`} onClick={() => setSelectedId(dialog.id)}>
      <span className="sales-dialog-avatar-wrap">
        <ContactAvatar avatarUrl={dialog.avatarUrl} initials={dialog.initials} background={dialog.avatarBg} className="sales-dialog-avatar" />
        <i style={{ background: modeDots[dialog.mode] }} />
      </span>
      <span className="sales-dialog-row-main">
        <span className="sales-dialog-row-agent">
          <small><ChannelGlyph provider={dialog.channel} /><span>{dialog.agentName}</span></small>
          {dialog.priority !== "NONE" && <PriorityBars priority={dialog.priority} />}
        </span>
        <span className="sales-dialog-row-title"><strong>{dialog.name}</strong><em>{dialog.time}</em></span>
        <span className="sales-dialog-row-preview">
          {dialog.lastIsOurs && <Icon name="reply" size={13} />}
          <small className={dialog.unread ? "unread" : ""}>{dialog.preview}</small>
          {dialog.unread > 0 && <b>{dialog.unread}</b>}
        </span>
        {(dialog.waitLabel || dialog.groupName || dialog.labels.length > 0) && (
          <span className="sales-dialog-row-badges">
            {dialog.waitLabel && <b className="sales-dialog-badge is-wait"><Icon name="clock" size={11} />{dialog.waitLabel}</b>}
            {dialog.groupName && <b className="sales-dialog-badge"><i className="is-round" style={{ background: dialog.groupColor }} />{dialog.groupName}</b>}
            {dialog.labels.map((label) => (
              <b className="sales-dialog-badge" key={label.id}><i style={{ background: label.color || "var(--n-5)" }} />{label.name}</b>
            ))}
          </span>
        )}
      </span>
    </button>
  );
}

const PRIORITY_TITLE: Record<string, string> = { HIGH: "Высокий", MEDIUM: "Средний", LOW: "Низкий" };
const PRIORITY_ON: Record<string, number> = { HIGH: 3, MEDIUM: 2, LOW: 1 };
const PRIORITY_COLOR: Record<string, string> = { HIGH: "#ff4d4f", MEDIUM: "#fa8c16", LOW: "var(--primary)" };

export function PriorityBars({ priority, placeholder = false }: { priority: "HIGH" | "MEDIUM" | "LOW" | "NONE"; placeholder?: boolean }) {
  if (priority === "NONE" && !placeholder) return null;
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
function ScopeSwitcher({ scope, counters, setScope, fallbackTitle, total }: { scope: DialogScope; counters: ConversationCounters | null; setScope: (scope: DialogScope) => void; fallbackTitle: string; total: number }) {
  const heading = scope.kind === "all" ? (counters ? "Все диалоги" : fallbackTitle) : scopeLabel(scope);
  if (!counters || (counters.groups.length === 0 && counters.agents.length <= 1)) {
    return <h2 className="sales-dialog-list-title">{heading}<small>{total}</small></h2>;
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
        <h2 className="sales-dialog-list-title">{heading}<small>{total}</small></h2>
        <Icon name="chevron" size={14} />
      </button>
    </Dropdown>
  );
}

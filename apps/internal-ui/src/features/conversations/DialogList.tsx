import { Dropdown } from "antd";
import { useCallback, type CSSProperties, type ReactNode, type UIEvent } from "react";

import { modeDots } from "./data";
import { ContactAvatar } from "./ContactAvatar";
import { Icon } from "../../shared/icons";
import { useResizableWidth } from "../../shared/useResizableWidth";
import { ChannelGlyph } from "../../shared/badges";
import { scopeLabel, type DialogScope } from "./ConversationWorkspace";
import { agentColorOf, groupColorOf } from "./model";
import type { ConversationCounters } from "./model";
import type { ConversationListItem, ListSort, ListTab } from "./types";
import { SearchInput } from "../../shared/ui-controls";
import { t } from "../../i18n";

export function DialogList({ title = t("common.conversations"), searchPlaceholder = t("conversations.search_by_contact_or_message"), viewerId = null, scope, counters, setScope, showScopeSwitcher = true, mobileHeader, hint, dialogs, total, hasMore, onLoadMore, narrowed, listTab, selectedId, search, errorText, sort, setSort, onCollapse, setSearch, setListTab, setSelectedId }: {
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
  viewerId?: number | null;
  hint?: ReactNode;
  dialogs: ConversationListItem[];
  // Размер всего охвата с учётом фильтров — считает сервер; dialogs держит лишь
  // загруженное окно.
  total: number;
  hasMore: boolean;
  onLoadMore: () => void;
  /** Список сужен поиском или вкладкой — пустота означает «не найдено». */
  narrowed: boolean;
  listTab: ListTab;
  selectedId: number;
  search: string;
  errorText?: string;
  setSearch: (value: string) => void;
  setListTab: (tab: ListTab) => void;
  setSelectedId: (id: number) => void;
}) {
  // Счётчик ждущих — из счётчиков охвата, а не из загруженного окна.
  const waitCount = counters?.waiting ?? 0;
  // Лента догружается прокруткой: следующее окно запрашивается на подходе к низу.
  const onScroll = useCallback((event: UIEvent<HTMLDivElement>) => {
    if (!hasMore) return;
    const node = event.currentTarget;
    if (node.scrollHeight - node.scrollTop - node.clientHeight < LOAD_TRIGGER_PX) onLoadMore();
  }, [hasMore, onLoadMore]);
  // Ширина списка: тянется за правый край (280–520px), запоминается в браузере.
  const listWidth = useResizableWidth("dialogList", { fallback: 323, min: 280, max: 520 });
  return (
    <section className={`sales-dialog-list ${listWidth.dragging ? "is-resizing" : ""}`} style={{ "--dialog-list-width": `${listWidth.width}px` } as CSSProperties}>
      <div className="pane-resizer" role="separator" aria-orientation="vertical" aria-label={t("conversations.conversation_list_width")} title={t("profile.drag_resize_double_click_reset")} onPointerDown={listWidth.onPointerDown} onDoubleClick={listWidth.reset} />
      {mobileHeader?.({ total })}
      <div className="sales-dialog-list-head">
        <div>
          {showScopeSwitcher
            ? <ScopeSwitcher scope={scope} counters={counters} setScope={setScope} fallbackTitle={title} total={total} viewerId={viewerId} />
            : <h2 className="sales-dialog-list-title">{scope.kind === "all" ? title : scopeLabel(scope)}<small>{total}</small></h2>}
          <span className="sales-dialog-list-tools">
            <Dropdown
              trigger={["click"]}
              placement="bottomRight"
              overlayClassName="app-dropdown"
              menu={{
                items: [
                  { key: "activity", label: <button type="button" className={sort === "activity" ? "is-checked" : ""} onClick={() => setSort("activity")}>{t("conversations.by_last_message")}</button> },
                  { key: "waiting", label: <button type="button" className={sort === "waiting" ? "is-checked" : ""} onClick={() => setSort("waiting")}>{t("conversations.by_waiting_time")}</button> },
                ],
              }}
            >
              <button type="button" aria-label={t("conversations.sorting")} title={sort === "activity" ? t("conversations.sorting_by_last_message") : t("conversations.sorting_by_waiting_time")}><Icon name="sort" size={15} /></button>
            </Dropdown>
            {onCollapse && <button type="button" aria-label={t("conversations.hide_list")} title={t("conversations.hide_list")} onClick={onCollapse}><Icon name="collapseLeft" size={15} /></button>}
          </span>
        </div>
        <SearchInput className="sales-dialog-search" placeholder={searchPlaceholder} value={search} onChange={setSearch} hotkey="/" />
      </div>
      <div className="sales-dialog-tabs">
        <DialogTab active={listTab === "all"} onClick={() => setListTab("all")}>{t("common.all")}</DialogTab>
        <DialogTab active={listTab === "mine"} onClick={() => setListTab("mine")}>{t("conversations.mine")}</DialogTab>
        <DialogTab active={listTab === "wait"} onClick={() => setListTab("wait")}>{t("conversations.waiting_for_operator")}{waitCount > 0 && <b>{waitCount}</b>}</DialogTab>
      </div>
      {hint}
      <div className="sales-dialog-list-body" onScroll={onScroll}>
        {errorText && <div className="sales-wait-note sales-load-error">{errorText}</div>}
        {/* Кадр S1: пустой список без призыва к действию. Под фильтром и
            поиском показывается, что ничего не нашлось, а не что диалогов нет. */}
        {!errorText && dialogs.length === 0 && (
          <div className="sales-dialog-list-empty">
            <span><Icon name={narrowed ? "search" : "message"} size={20} /></span>
            <p>{narrowed ? t("conversations.no_conversations_found") : t("conversations.conversations_appear_once_customers_write")}</p>
          </div>
        )}
        {dialogs.map((dialog) => <DialogListItem dialog={dialog} active={dialog.id === selectedId} setSelectedId={setSelectedId} key={dialog.id} />)}
      </div>
    </section>
  );
}

// Ближе этого к низу списка — запрашиваем следующее окно.
const LOAD_TRIGGER_PX = 320;

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
          {dialog.lastIsVoice && <Icon name="mic" size={13} />}
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

const PRIORITY_TITLE: Record<string, string> = { HIGH: t("conversations.high"), MEDIUM: t("conversations.medium"), LOW: t("conversations.low") };
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

// Переключатель охвата (дизайн-базлайн v2 A1): Все диалоги · Группы · Агенты ·
// Ответственный. Дерево фильтров живёт в заголовке списка, сайдбар остаётся плоским.
function ScopeSwitcher({ scope, counters, setScope, fallbackTitle, total, viewerId }: { scope: DialogScope; counters: ConversationCounters | null; setScope: (scope: DialogScope) => void; fallbackTitle: string; total: number; viewerId: number | null }) {
  const heading = scope.kind === "all" ? (counters ? t("profile.all_conversations") : fallbackTitle) : scopeLabel(scope);
  if (!counters || (counters.groups.length === 0 && counters.agents.length <= 1 && counters.assignees.length === 0)) {
    return <h2 className="sales-dialog-list-title">{heading}<small>{total}</small></h2>;
  }
  const checked = (candidate: DialogScope) =>
    scope.kind === candidate.kind && ("id" in scope && "id" in candidate ? scope.id === candidate.id : true) ? "is-checked" : "";
  const item = (key: string, target: DialogScope, icon: ReactNode, label: string, count: number) => ({
    key,
    label: <button type="button" className={checked(target)} onClick={() => setScope(target)}>{icon}<span>{label}</span><small>{count}</small></button>,
  });
  const head = (key: string, label: string) => ({ key, type: "group" as const, label });
  const items = [
    item("all", { kind: "all" }, <Icon name="inbox" size={15} />, t("profile.all_conversations"), counters.all),
    ...(counters.groups.length > 0
      ? [
          head("groups-head", t("common.groups")),
          ...counters.groups.map((group) => item(`group-${group.id}`, { kind: "group", id: group.id, label: group.name }, <i className="scope-dot" style={{ background: groupColorOf(group.id, group.color) }} />, group.name, group.count)),
          item("ungrouped", { kind: "ungrouped" }, <i className="scope-dot is-muted" />, t("common.no_group"), counters.ungrouped),
        ]
      : []),
    ...(counters.agents.length > 0
      ? [
          head("agents-head", t("common.agents")),
          ...counters.agents.map((agent) => {
            const color = agentColorOf(agent.id);
            return item(`agent-${agent.id}`, { kind: "agent", id: agent.id, label: agent.name }, <span className="scope-agent" style={{ color, background: `color-mix(in srgb, ${color} 16%, var(--surface-card))` }}><Icon name="robot" size={11} /></span>, agent.name, agent.count);
          }),
        ]
      : []),
    ...(counters.assignees.length > 0
      ? [
          head("assignees-head", t("common.assignee")),
          ...counters.assignees.map((assignee) => item(`assignee-${assignee.id}`, { kind: "assignee", id: assignee.id, label: assignee.name }, <span className={`scope-avatar ${assignee.avatarUrl ? "has-photo" : ""}`}>{assignee.avatarUrl ? <img src={assignee.avatarUrl} alt="" /> : initialsOf(assignee.name)}</span>, assignee.id === viewerId ? `${assignee.name}${t("common.you_suffix")}` : assignee.name, assignee.count)),
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

function initialsOf(name: string): string {
  return name.split(/\s+/).map((part) => part[0] ?? "").join("").slice(0, 2).toUpperCase();
}

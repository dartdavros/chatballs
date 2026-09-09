import { Dropdown } from "antd";
import { useEffect, useState } from "react";

import { Icon } from "../../shared/icons";
import { SearchInput } from "../../shared/ui-controls";
import { PriorityBars } from "./DialogList";
import { useEmployeeDirectory } from "./useEmployeeDirectory";
import { statusFor } from "./data";
import {
  agentColorOf,
  controlModeOf,
  createConversationLabel,
  fetchConversationLabels,
  groupColorOf,
  setConversationArchived,
  setConversationAssignee,
  setConversationGroup,
  setConversationLabels,
  setConversationNote,
  setConversationPriority,
  type ApiConversation,
  type ConversationLabelRef,
  type ConversationPriority,
} from "./model";
import type { EmployeeGroupRef } from "../../types";
import { t } from "../../i18n";

// Блок «Диалог» контекст-панели (дизайн-базлайн v2, решение 5): Ответственный,
// Группа, Приоритет — полноширинные селекты; Агент и Режим — read-only в две
// колонки; Метки — чипы с «+ Добавить»; Начат. Заметка — отдельная жёлтая карточка.

const PRIORITY_OPTIONS: Array<[ConversationPriority, string]> = [
  ["HIGH", t("conversations.high")],
  ["MEDIUM", t("conversations.medium")],
  ["LOW", t("conversations.low")],
  ["NONE", t("conversations.not_set")],
];
const PRIORITY_TEXT: Record<ConversationPriority, string> = {
  HIGH: "var(--error-text)",
  MEDIUM: "#d46b08",
  LOW: "var(--primary-text)",
  NONE: "var(--n-4)",
};

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase();
}

export function DialogControls({
  detail,
  groups,
  applyConversation,
  viewerId = null,
}: {
  detail: ApiConversation;
  groups: Array<EmployeeGroupRef & { color?: string }>;
  applyConversation: (updated: ApiConversation) => void;
  viewerId?: number | null;
}) {
  const directory = useEmployeeDirectory();
  const [busy, setBusy] = useState(false);
  const [errorText, setErrorText] = useState("");
  const [collapsed, setCollapsed] = useState(false);
  const [labels, setLabels] = useState<ConversationLabelRef[]>([]);
  const [newLabel, setNewLabel] = useState("");

  useEffect(() => {
    setNewLabel("");
    setErrorText("");
  }, [detail.id]);

  useEffect(() => {
    fetchConversationLabels().then(setLabels).catch(() => setLabels([]));
  }, []);

  async function run(action: () => Promise<ApiConversation>) {
    setBusy(true);
    setErrorText("");
    try {
      applyConversation(await action());
    } catch (error) {
      setErrorText(error instanceof Error ? error.message : t("common.could_not_save"));
    } finally {
      setBusy(false);
    }
  }

  async function addLabel(id?: number) {
    let labelId = id;
    setBusy(true);
    setErrorText("");
    try {
      if (labelId === undefined) {
        const name = newLabel.trim();
        if (!name) return;
        const label = await createConversationLabel(name);
        setLabels((current) => (current.some((item) => item.id === label.id) ? current : [...current, label]));
        labelId = label.id;
        setNewLabel("");
      }
      const ids = [...new Set([...detail.labels.map((item) => item.id), labelId])];
      applyConversation(await setConversationLabels(detail.id, ids));
    } catch (error) {
      setErrorText(error instanceof Error ? error.message : t("conversations.could_not_add_label"));
    } finally {
      setBusy(false);
    }
  }

  const assignedIds = new Set(detail.labels.map((item) => item.id));
  const availableLabels = labels.filter((item) => !assignedIds.has(item.id));
  const assignee = detail.assignedOperator;
  const assigneeLabel = assignee ? `${assignee.name}${viewerId != null && assignee.id === viewerId ? t("common.you_suffix") : ""}` : t("conversations.unassigned");
  const status = statusFor(controlModeOf(detail), assignee?.name);
  const priorityLabel = PRIORITY_OPTIONS.find(([value]) => value === detail.priority)?.[1] ?? t("conversations.not_set");
  const canEdit = directory.employees.length > 0 || groups.length > 0;

  return (
    <>
      <section className="ctx-section">
        <div className="ctx-section-head">
          <h4>{t("conversations.conversation")}</h4>
          <button type="button" aria-label={collapsed ? t("profile.expand") : t("conversations.collapse")} className={collapsed ? "is-collapsed" : ""} onClick={() => setCollapsed((value) => !value)}><Icon name="chevron" size={14} /></button>
        </div>
        {!collapsed && (
          <div className="ctx-fields">
            {errorText && <p className="ctx-error">{errorText}</p>}

            <label className="ctx-label">{t("common.assignee")}</label>
            <Dropdown
              disabled={busy || (directory.employees.length === 0 && !directory.query)}
              trigger={["click"]}
              overlayClassName="app-dropdown ctx-menu"
              menu={{
                items: [
                  // Строка поиска появляется, когда коллег больше, чем помещается
                  // в выдачу справочника: маленькой команде она не нужна.
                  ...(directory.hasMore || directory.query
                    ? [{
                      key: "search",
                      type: "group" as const,
                      label: (
                        <SearchInput
                          className="ctx-menu-search"
                          placeholder={t("conversations.name_or_email")}
                          value={directory.query}
                          onChange={directory.setQuery}
                        />
                      ),
                    }]
                    : []),
                  { key: "none", label: <button type="button" className={assignee ? "" : "is-checked"} onClick={() => void run(() => setConversationAssignee(detail.id, null))}><span className="ctx-avatar-empty" /><span>{t("conversations.unassigned")}</span>{!assignee && <Icon name="check" size={15} />}</button> },
                  ...directory.employees.map((employee) => ({
                    key: employee.id,
                    label: <button type="button" className={assignee?.id === employee.id ? "is-checked" : ""} onClick={() => void run(() => setConversationAssignee(detail.id, employee.id))}><SmallAvatar name={employee.name} avatarUrl={employee.avatarUrl} /><span>{employee.name}{viewerId === employee.id ? t("common.you_suffix") : ""}</span>{assignee?.id === employee.id && <Icon name="check" size={15} />}</button>,
                  })),
                ],
              }}
            >
              <button type="button" className={`ctx-select ${assignee ? "" : "is-empty"}`}>
                {assignee ? <SmallAvatar name={assignee.name} avatarUrl={assignee.avatarUrl} /> : <span className="ctx-avatar-empty" />}
                <span>{assigneeLabel}</span>
                {canEdit && <Icon name="chevron" size={14} />}
              </button>
            </Dropdown>

            <label className="ctx-label">{t("common.group")}</label>
            <Dropdown
              disabled={busy || groups.length === 0}
              trigger={["click"]}
              overlayClassName="app-dropdown ctx-menu"
              menu={{
                // Кадр G: заголовок «Перенести в группу», отмеченный пункт с галочкой, подпись внизу.
                items: [
                  { key: "title", type: "group" as const, label: t("conversations.move_group") },
                  { key: "none", label: <button type="button" className={detail.group ? "" : "is-checked"} onClick={() => void run(() => setConversationGroup(detail.id, null))}><i className="ctx-dot is-muted" /><span>{t("common.no_group")}</span>{!detail.group && <Icon name="check" size={15} />}</button> },
                  ...groups.map((group) => ({
                    key: group.id,
                    label: <button type="button" className={detail.group?.id === group.id ? "is-checked" : ""} onClick={() => void run(() => setConversationGroup(detail.id, group.id))}><i className="ctx-dot" style={{ background: groupColorOf(group.id, group.color) }} /><span>{group.name}</span>{detail.group?.id === group.id && <Icon name="check" size={15} />}</button>,
                  })),
                  { key: "note", type: "group" as const, className: "ctx-menu-note", label: t("conversations.conversation_without_group_visible_every") },
                ],
              }}
            >
              <button type="button" className="ctx-select">
                <i className={`ctx-dot ${detail.group ? "" : "is-muted"}`} style={detail.group ? { background: groupColorOf(detail.group.id, detail.group.color) } : undefined} />
                <span>{detail.group?.name ?? t("common.no_group")}</span>
                {canEdit && <Icon name="chevron" size={14} />}
              </button>
            </Dropdown>

            <label className="ctx-label">{t("conversations.priority")}</label>
            <Dropdown
              disabled={busy}
              trigger={["click"]}
              overlayClassName="app-dropdown ctx-menu"
              menu={{
                items: PRIORITY_OPTIONS.map(([value, label]) => ({
                  key: value,
                  label: <button type="button" className={detail.priority === value ? "is-checked" : ""} onClick={() => void run(() => setConversationPriority(detail.id, value))}><PriorityBars priority={value} placeholder /><span>{label}</span>{detail.priority === value && <Icon name="check" size={15} />}</button>,
                })),
              }}
            >
              <button type="button" className="ctx-select">
                <PriorityBars priority={detail.priority} placeholder />
                <span style={{ color: PRIORITY_TEXT[detail.priority], fontWeight: detail.priority === "NONE" ? 500 : 600 }}>{priorityLabel}</span>
                <Icon name="chevron" size={14} />
              </button>
            </Dropdown>

            <div className="ctx-grid">
              <div>
                <label className="ctx-label">{t("common.agent")}</label>
                <div className="ctx-readonly" style={{ color: agentColorOf(detail.channel.id) }}><Icon name="robot" size={14} />{detail.channel.name}</div>
              </div>
              <div>
                <label className="ctx-label">{t("conversations.mode")}</label>
                <div className="ctx-readonly is-mode" style={{ color: status.color, background: status.bg, borderColor: status.border }}><i style={{ background: status.dot }} />{status.label}</div>
              </div>
            </div>

            <label className="ctx-label">{t("conversations.labels")}</label>
            <div className="ctx-labels">
              <Dropdown
                disabled={busy}
                trigger={["click"]}
                overlayClassName="app-dropdown is-wide ctx-labels-menu"
                menu={{
                  items: [
                    ...availableLabels.map((label) => ({
                      key: label.id,
                      label: <button type="button" onClick={() => void addLabel(label.id)}><i className="ctx-dot is-square" style={{ background: label.color || "var(--n-5)" }} />{label.name}</button>,
                    })),
                    {
                      key: "new",
                      label: (
                        <div className="ctx-new-label" onClick={(event) => event.stopPropagation()}>
                          <input
                            placeholder={t("conversations.new_label")}
                            value={newLabel}
                            onChange={(event) => setNewLabel(event.target.value)}
                            onKeyDown={(event) => {
                              if (event.key === "Enter") {
                                event.preventDefault();
                                void addLabel();
                              }
                            }}
                          />
                          <button type="button" disabled={busy || !newLabel.trim()} onClick={() => void addLabel()}><Icon name="plus" size={13} /></button>
                        </div>
                      ),
                    },
                  ],
                }}
              >
                <button type="button" className="ctx-add-label"><Icon name="plus" size={13} />{t("conversations.add")}</button>
              </Dropdown>
              {detail.labels.map((label) => (
                <b className="ctx-label-chip" key={label.id}>
                  <i style={{ background: label.color || "var(--n-5)" }} />
                  {label.name}
                  <button
                    aria-label={t("conversations.remove_label", { name: label.name })}
                    disabled={busy}
                    type="button"
                    onClick={() => void run(() => setConversationLabels(detail.id, detail.labels.filter((item) => item.id !== label.id).map((item) => item.id)))}
                  >
                    ×
                  </button>
                </b>
              ))}
            </div>

            <div className="ctx-meta-row"><span>{t("conversations.started")}</span><span>{startedLabel(detail.createdAt)}</span></div>
          </div>
        )}
      </section>

      <NoteSection detail={detail} busy={busy} onSave={(note) => run(() => setConversationNote(detail.id, note))} />
    </>
  );
}

function NoteSection({ detail, busy, onSave }: { detail: ApiConversation; busy: boolean; onSave: (note: string) => Promise<void> }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(detail.note);

  useEffect(() => {
    setEditing(false);
    setDraft(detail.note);
  }, [detail.id, detail.note]);

  return (
    <section className="ctx-section is-note">
      <div className="ctx-section-head">
        <h4>{t("conversations.note")}</h4>
        <button type="button" aria-label={t("conversations.edit_note")} onClick={() => setEditing(true)}><Icon name="edit" size={14} /></button>
      </div>
      {editing ? (
        <div className="ctx-note is-editing">
          <textarea autoFocus disabled={busy} placeholder={t("conversations.internal_note_customer_does_not")} rows={3} value={draft} onChange={(event) => setDraft(event.target.value)} />
          <div className="ctx-note-actions">
            <button type="button" disabled={busy} onClick={() => { setDraft(detail.note); setEditing(false); }}>{t("common.cancel")}</button>
            <button type="button" className="primary" disabled={busy} onClick={() => void onSave(draft).then(() => setEditing(false))}>{t("common.save")}</button>
          </div>
        </div>
      ) : (
        <div className={`ctx-note ${detail.note ? "" : "is-empty"}`} onClick={() => setEditing(true)}>{detail.note || t("conversations.no_notes")}</div>
      )}
    </section>
  );
}

// «сегодня, 17:02» · «вчера, 11:05» · «12 авг, 09:30»
export function startedLabel(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const time = date.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
  if (date.toDateString() === now.toDateString()) return t("time.today_comma", { time });
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (date.toDateString() === yesterday.toDateString()) return t("time.yesterday_comma", { time });
  return `${date.toLocaleDateString("ru-RU", { day: "numeric", month: "short" }).replace(".", "")}, ${time}`;
}

export function archiveConversationAction(
  detail: ApiConversation,
  applyConversation: (updated: ApiConversation) => void,
  onError: (text: string) => void,
): Promise<boolean> {
  return setConversationArchived(detail.id, true)
    .then((updated) => {
      applyConversation(updated);
      return true;
    })
    .catch((error) => {
      onError(error instanceof Error ? error.message : t("conversations.could_not_delete_conversation"));
      return false;
    });
}

// Аватар 22px в поле «Ответственный»: фото сотрудника или инициалы.
function SmallAvatar({ name, avatarUrl }: { name: string; avatarUrl?: string | null }) {
  if (avatarUrl) return <span className="ctx-avatar-small has-photo"><img src={avatarUrl} alt="" /></span>;
  return <span className="ctx-avatar-small">{initials(name)}</span>;
}

import { Modal } from "antd";
import { useEffect, useState } from "react";

import { api } from "../../api/client";
import { Icon } from "../../shared/icons";
import { fetchConversationCounters, groupColorOf } from "../conversations/model";
import { Button } from "../../shared/ui-controls";
import type { EmployeeGroup } from "../../types";
import { t, tn } from "../../i18n";

// Раздел «Группы» (дизайн-базлайн v2, кадр N2): строка — цветная точка · имя ·
// состав · диалоги · изменить/удалить; создание — одно поле в подвале списка.
// Состав группы редактируется на карточке сотрудника.

const GROUP_COLORS: Array<[string, string]> = [
  ["#1677ff", t("shared.blue")],
  ["#2aa876", t("settings.green")],
  ["#eb2f96", t("settings.pink")],
  ["#fa8c16", t("shared.orange")],
  ["#722ed1", t("settings.purple")],
  ["#13c2c2", t("shared.teal")],
  ["#52c41a", t("settings.lime")],
  ["#f5222d", t("settings.red")],
];

export function GroupsSettingsCard({ groups, reload }: { groups: EmployeeGroup[]; reload: () => void }) {
  const [name, setName] = useState("");
  const [renameColor, setRenameColor] = useState("");
  const [creating, setCreating] = useState(false);
  const [errorText, setErrorText] = useState("");
  const [renaming, setRenaming] = useState<EmployeeGroup | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [deleting, setDeleting] = useState<EmployeeGroup | null>(null);
  const [modalError, setModalError] = useState("");
  // Сколько диалогов в группе — из тех же счётчиков, что и охват чата.
  const [dialogs, setDialogs] = useState<Record<number, number>>({});

  useEffect(() => {
    fetchConversationCounters()
      .then((counters) => setDialogs(Object.fromEntries(counters.groups.map((group) => [group.id, group.count]))))
      .catch(() => undefined);
  }, [groups.length]);

  async function create() {
    const trimmed = name.trim();
    if (!trimmed || creating) return;
    setCreating(true);
    setErrorText("");
    try {
      await api("/api/v1/company/groups/", { method: "POST", body: JSON.stringify({ name: trimmed }) });
      setName("");
      reload();
    } catch (caught) {
      setErrorText(caught instanceof Error ? caught.message : t("settings.could_not_create_group"));
    } finally {
      setCreating(false);
    }
  }

  async function rename() {
    if (!renaming) return;
    setModalError("");
    try {
      await api(`/api/v1/company/groups/${renaming.id}/`, { method: "PATCH", body: JSON.stringify({ name: renameValue.trim(), color: renameColor }) });
      setRenaming(null);
      reload();
    } catch (caught) {
      setModalError(caught instanceof Error ? caught.message : t("settings.could_not_rename"));
    }
  }

  async function remove() {
    if (!deleting) return;
    setModalError("");
    try {
      await api(`/api/v1/company/groups/${deleting.id}/`, { method: "DELETE" });
      setDeleting(null);
      reload();
    } catch (caught) {
      setModalError(caught instanceof Error ? caught.message : t("settings.could_not_delete_group"));
    }
  }

  return (
    <>
      <div className="table-card settings-groups-card">
        {groups.length === 0 && <p className="settings-groups-empty">{t("admin.there_no_groups_yet_so_2")}</p>}
        {groups.map((group) => (
          <div className="settings-group-row" key={group.id}>
            <i className="chat-scope-dot" style={{ background: groupColorOf(group.id, group.color) }} />
            <strong>{group.name}</strong>
            <small>{t("admin.people_count", { count: group.memberCount })}</small>
            <small className="settings-group-dialogs">{tn("plural.conversations", dialogs[group.id] ?? 0)}</small>
            <div className="settings-group-actions">
              <button aria-label={t("common.edit")} title={t("common.edit")} type="button" onClick={() => { setModalError(""); setRenaming(group); setRenameValue(group.name); setRenameColor(group.color || groupColorOf(group.id)); }}><Icon name="edit" size={14} /></button>
              <button aria-label={t("common.delete")} title={t("common.delete")} className="is-danger" type="button" onClick={() => { setModalError(""); setDeleting(group); }}><Icon name="trash" size={14} /></button>
            </div>
          </div>
        ))}
        <div className="settings-group-create">
          <input
            placeholder={t("settings.new_group_name")}
            value={name}
            onChange={(event) => setName(event.target.value)}
            onKeyDown={(event) => { if (event.key === "Enter") void create(); }}
          />
          <Button variant="secondary" icon="plus" disabled={!name.trim() || creating} onClick={() => void create()}>{t("ai.create_2")}</Button>
        </div>
      </div>
      {errorText && <div className="settings-section-error">{errorText}</div>}
      <p className="settings-section-note">{t("settings.group_membership_edited_operator_card")}</p>
      {renaming && (
        <Modal open title={t("common.group")} onCancel={() => setRenaming(null)} footer={null} destroyOnClose>
          <div className="integration-form">
            <input className="settings-modal-input" value={renameValue} onChange={(event) => setRenameValue(event.target.value)} />
            {/* Цвет точки группы в чате (дизайн-базлайн v2) — тот же стандарт свотчей, что у акцента. */}
            <div className="appearance-accents settings-group-colors">
              {GROUP_COLORS.map(([value, label]) => (
                <button aria-label={label} className={renameColor === value ? "active" : ""} key={value} type="button" style={{ background: value, "--accent-ring": value } as React.CSSProperties} onClick={() => setRenameColor(value)} />
              ))}
            </div>
            {modalError && <div className="integration-form-error">{modalError}</div>}
            <div className="integration-form-actions">
              <Button variant="secondary" onClick={() => setRenaming(null)}>{t("common.cancel")}</Button>
              <Button variant="primary" disabled={!renameValue.trim()} onClick={() => void rename()}>{t("common.save")}</Button>
            </div>
          </div>
        </Modal>
      )}
      {deleting && (
        <Modal open title={t("settings.delete_group")} onCancel={() => setDeleting(null)} footer={null} destroyOnClose>
          <div className="integration-form">
            <p>{t("admin.group_will_be_deleted", { name: deleting.name })}</p>
            {modalError && <div className="integration-form-error">{modalError}</div>}
            <div className="integration-form-actions">
              <Button variant="secondary" onClick={() => setDeleting(null)}>{t("common.cancel")}</Button>
              <Button variant="danger-outline" onClick={() => void remove()}>{t("common.delete")}</Button>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
}

import { Modal } from "antd";
import { useState } from "react";

import { api } from "../../api/client";
import { Icon } from "../../shared/icons";
import { groupColorOf } from "../conversations/model";
import { Button } from "../../shared/ui-controls";
import type { EmployeeGroup } from "../../types";

// Секция «Группы» экрана настроек (SPEC-HUB-0031 §8.4/§8.6): список с числом
// участников, создание — одно поле, переименование и удаление. Состав группы
// редактируется на карточке сотрудника.

const GROUP_COLORS: Array<[string, string]> = [
  ["#1677ff", "Синий"],
  ["#2aa876", "Зелёный"],
  ["#eb2f96", "Розовый"],
  ["#fa8c16", "Оранжевый"],
  ["#722ed1", "Фиолетовый"],
  ["#13c2c2", "Бирюзовый"],
  ["#52c41a", "Салатовый"],
  ["#f5222d", "Красный"],
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
      setErrorText(caught instanceof Error ? caught.message : "Не удалось создать группу");
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
      setModalError(caught instanceof Error ? caught.message : "Не удалось переименовать");
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
      setModalError(caught instanceof Error ? caught.message : "Не удалось удалить группу");
    }
  }

  return (
    <div className="profile-card">
      <h3>Группы</h3>
      <p className="settings-section-note">Видимость диалогов и охват чата. Состав группы — на карточке сотрудника.</p>
      <div className="settings-groups-list">
        {groups.length === 0 && <p className="settings-section-note">Групп пока нет — все видят все диалоги.</p>}
        {groups.map((group) => (
          <div className="settings-group-row" key={group.id}>
            <i className="chat-scope-dot" style={{ background: groupColorOf(group.id, group.color) }} />
            <strong>{group.name}</strong>
            <small>{group.memberCount} чел.</small>
            <button aria-label="Изменить" type="button" onClick={() => { setModalError(""); setRenaming(group); setRenameValue(group.name); setRenameColor(group.color || groupColorOf(group.id)); }}><Icon name="edit" size={14} /></button>
            <button aria-label="Удалить" type="button" onClick={() => { setModalError(""); setDeleting(group); }}><Icon name="trash" size={14} /></button>
          </div>
        ))}
      </div>
      <div className="settings-group-create">
        <input
          placeholder="Название новой группы"
          value={name}
          onChange={(event) => setName(event.target.value)}
          onKeyDown={(event) => { if (event.key === "Enter") void create(); }}
        />
        <Button variant="secondary" icon="plus" disabled={!name.trim() || creating} onClick={() => void create()}>Создать</Button>
      </div>
      {errorText && <div className="settings-section-error">{errorText}</div>}
      {renaming && (
        <Modal open title="Группа" onCancel={() => setRenaming(null)} footer={null} destroyOnClose>
          <div className="integration-form">
            <input className="settings-modal-input" value={renameValue} onChange={(event) => setRenameValue(event.target.value)} />
            {/* Цвет точки группы в чате (дизайн-базлайн v2) — тот же стандарт свотчей, что у акцента. */}
            <div className="appearance-accents settings-group-colors">
              {GROUP_COLORS.map(([value, label]) => (
                <button aria-label={label} className={renameColor === value ? "active" : ""} key={value} type="button" style={{ background: value }} onClick={() => setRenameColor(value)} />
              ))}
            </div>
            {modalError && <div className="integration-form-error">{modalError}</div>}
            <div className="integration-form-actions">
              <Button variant="secondary" onClick={() => setRenaming(null)}>Отмена</Button>
              <Button variant="primary" disabled={!renameValue.trim()} onClick={() => void rename()}>Сохранить</Button>
            </div>
          </div>
        </Modal>
      )}
      {deleting && (
        <Modal open title="Удалить группу?" onCancel={() => setDeleting(null)} footer={null} destroyOnClose>
          <div className="integration-form">
            <p>{`«${deleting.name}» будет удалена; её диалоги станут «Без группы».`}</p>
            {modalError && <div className="integration-form-error">{modalError}</div>}
            <div className="integration-form-actions">
              <Button variant="secondary" onClick={() => setDeleting(null)}>Отмена</Button>
              <Button variant="danger-outline" onClick={() => void remove()}>Удалить</Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

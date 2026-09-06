import { useEffect, useState, type ReactNode } from "react";

import { api } from "../../api/client";
import { Icon } from "../../shared/icons";
import { groupColorOf } from "../conversations/model";
import type { Employee, EmployeeGroup, Role } from "../../types";

export function EmployeeCreateDrawer({ groups, onClose, onCreated, open }: {
  groups: EmployeeGroup[];
  onClose: () => void;
  onCreated: (employee: Employee) => void;
  open: boolean;
}) {
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<Role>("EMPLOYEE");
  const [positionTitle, setPositionTitle] = useState("");
  const [groupIds, setGroupIds] = useState<number[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    setFullName(""); setPhone(""); setEmail(""); setRole("EMPLOYEE");
    setPositionTitle(""); setGroupIds([]); setError("");
  }, [open]);

  if (!open) return null;
  const canSubmit = Boolean(fullName.trim() && email.trim() && positionTitle.trim() && !submitting);

  function toggleGroup(groupId: number) {
    setGroupIds((items) => items.includes(groupId)
      ? items.filter((item) => item !== groupId)
      : [...items, groupId]);
  }

  async function submit() {
    if (!canSubmit) return;
    setSubmitting(true); setError("");
    try {
      const payload = await api<{ employee: Employee }>("/api/v1/employees/operators/", {
        method: "POST",
        body: JSON.stringify({ fullName, phone, email, role, positionTitle, groupIds }),
      });
      onCreated(payload.employee);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Ошибка создания");
    } finally {
      setSubmitting(false);
    }
  }

  return <>
    <button className="employee-drawer-scrim" aria-label="Закрыть форму" onClick={onClose} />
    <aside className="employee-create-drawer" aria-label="Новый сотрудник">
      <header><div><strong>Новый сотрудник</strong><span>Учётные данные · роль · группы</span></div><button aria-label="Закрыть" onClick={onClose}><Icon name="xCircle" size={19} /></button></header>
      <div className="employee-create-body">
        <CreateStep number="1" title="Учётные данные"><div className="employee-create-grid"><CreateField label="Имя" value={fullName} onChange={setFullName} placeholder="Имя и фамилия" /><CreateField label="Телефон" value={phone} onChange={setPhone} placeholder="+7 …" /><CreateField className="wide" label="Рабочий email · используется для входа" value={email} onChange={setEmail} placeholder="name@company.ru" mono /></div></CreateStep>
        <CreateStep number="2" title="Роль"><div className="employee-role-options"><RoleOption active={role === "EMPLOYEE"} description="Работает в одном окне — чате. Видит диалоги своих групп, диалоги без группы и назначенные ему." label="Сотрудник" onClick={() => setRole("EMPLOYEE")} /><RoleOption active={role === "ADMIN"} description="Полный доступ, идентичен владельцу. Единственное отличие владельца — его нельзя удалить." label="Администратор" onClick={() => setRole("ADMIN")} /></div></CreateStep>
        <CreateStep number="3" title="Должность и группы"><div className="employee-create-grid"><CreateField className="wide" label="Должность" value={positionTitle} onChange={setPositionTitle} placeholder="напр. Оператор" /></div>{role === "EMPLOYEE" && (groups.length ? <div className="employee-create-profiles">{groups.map((group) => { const active = groupIds.includes(group.id); return <label className={active ? "selected" : ""} key={group.id}><button type="button" aria-pressed={active} onClick={() => toggleGroup(group.id)}><i>{active && <Icon name="check" size={11} />}</i><span><strong><i className="chat-scope-dot" style={{ background: groupColorOf(group.id, group.color) }} />{group.name}</strong><small>{group.memberCount} сотр.</small></span></button></label>; })}<p>Без групп сотрудник видит только диалоги без группы. Группы можно изменить позже.</p></div> : <p>Групп пока нет — сотрудник будет видеть все диалоги. Группы создаются на странице сотрудников.</p>)}</CreateStep>
      </div>
      <footer><span>{error || "Пароль первичного доступа отправится на email"}</span><div><button className="secondary-button" onClick={onClose}>Отмена</button><button className="primary-button" disabled={!canSubmit} onClick={submit}>{submitting ? "Создание" : "Создать сотрудника"}</button></div></footer>
    </aside>
  </>;
}

function CreateStep({ children, number, title }: { children: ReactNode; number: string; title: string }) { return <section className="employee-create-step"><h3><i>{number}</i>{title}</h3>{children}</section>; }
function CreateField({ className = "", label, mono = false, onChange, placeholder, value }: { className?: string; label: string; mono?: boolean; onChange: (value: string) => void; placeholder: string; value: string }) { return <label className={`employee-create-field ${className}`}><span>{label}</span><input className={mono ? "mono" : ""} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} /></label>; }
function RoleOption({ active, description, label, onClick }: { active: boolean; description: string; label: string; onClick: () => void }) { return <button className={active ? "active" : ""} type="button" onClick={onClick}><i>{active && <span />}</i><span><strong>{label}</strong><small>{description}</small></span></button>; }

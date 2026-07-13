import { useEffect, useMemo, useState, type ReactNode } from "react";

import { api } from "../../api/client";
import { Icon } from "../../shared/icons";
import type { AccessProfile, Department, Employee, Role, ScopeType, SessionUser } from "../../types";

type DraftAssignment = { profileId: number; scopeType: ScopeType };

export function EmployeeCreateDrawer({ departments, onClose, onCreated, open, profiles, user }: {
  departments: Department[];
  onClose: () => void;
  onCreated: (employee: Employee) => void;
  open: boolean;
  profiles: AccessProfile[];
  user: SessionUser;
}) {
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<Role>("EMPLOYEE");
  const [positionTitle, setPositionTitle] = useState("");
  const [department, setDepartment] = useState("");
  const [assignments, setAssignments] = useState<DraftAssignment[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const assignableProfiles = useMemo(() => profiles.filter((profile) => profile.isActive && !profile.isSystem), [profiles]);

  useEffect(() => {
    if (!open) return;
    setFullName(""); setPhone(""); setEmail(""); setRole("EMPLOYEE");
    setPositionTitle(""); setDepartment(""); setAssignments([]); setError("");
  }, [open]);

  if (!open) return null;
  const selected = new Map(assignments.map((assignment) => [assignment.profileId, assignment]));
  const validAssignments = assignments.every((assignment) => assignment.scopeType !== "DEPARTMENT" || Boolean(department));
  const canSubmit = Boolean(fullName.trim() && email.trim() && positionTitle.trim() && validAssignments && !submitting);

  function toggleProfile(profile: AccessProfile) {
    const current = selected.get(profile.id);
    if (current) {
      setAssignments((items) => items.filter((item) => item.profileId !== profile.id));
      return;
    }
    const scopeType = profile.allowedScopes.includes("DEPARTMENT") ? "DEPARTMENT" : "ORGANIZATION";
    setAssignments((items) => [...items, { profileId: profile.id, scopeType }]);
  }

  function changeScope(profileId: number, scopeType: ScopeType) {
    setAssignments((items) => items.map((item) => item.profileId === profileId ? { ...item, scopeType } : item));
  }

  async function submit() {
    if (!canSubmit) return;
    setSubmitting(true); setError("");
    try {
      const payload = await api<{ employee: Employee }>("/api/v1/employees/operators/", {
        method: "POST",
        body: JSON.stringify({
          fullName, phone, email, role, positionTitle, department,
          accessAssignments: role === "EMPLOYEE" ? assignments.map((assignment) => ({
            ...assignment,
            departmentId: assignment.scopeType === "DEPARTMENT"
              ? departments.find((item) => item.code === department)?.id ?? null
              : null,
          })) : [],
        }),
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
      <header><div><strong>Новый сотрудник</strong><span>Учётные данные · роль · размещение · доступ</span></div><button aria-label="Закрыть" onClick={onClose}><Icon name="xCircle" size={19} /></button></header>
      <div className="employee-create-body">
        <CreateStep number="1" title="Учётные данные"><div className="employee-create-grid"><CreateField label="Имя" value={fullName} onChange={setFullName} placeholder="Имя и фамилия" /><CreateField label="Телефон" value={phone} onChange={setPhone} placeholder="+7 …" /><CreateField className="wide" label="Рабочий email · используется для входа" value={email} onChange={setEmail} placeholder="name@edevs.tech" mono /></div></CreateStep>
        <CreateStep number="2" title="Системная роль"><div className="employee-role-options"><RoleOption active={role === "EMPLOYEE"} description="Рабочий доступ только через назначенные профили и scopes. Без назначений — только self-service." label="Сотрудник" onClick={() => setRole("EMPLOYEE")} />{user.role === "OWNER" && <RoleOption active={role === "ADMIN"} description="Все обычные capability организации. Не управляет владельцем и другими администраторами. Создаёт только OWNER." label="Администратор" onClick={() => setRole("ADMIN")} />}</div></CreateStep>
        <CreateStep number="3" title="Должность и размещение"><div className="employee-create-grid"><CreateField label="Должность ·" value={positionTitle} onChange={setPositionTitle} placeholder="напр. Менеджер по продажам" /><label className="employee-create-field"><span>Размещение</span><select value={department} onChange={(event) => setDepartment(event.target.value)}><option value="">Верхний уровень компании</option>{departments.map((item) => <option value={item.code} key={item.id}>{item.name}</option>)}</select></label></div><p>Должность вводится вручную и не выводится из роли. Основной отдел описывает оргструктуру, но не выдаёт прав.</p></CreateStep>
        <CreateStep muted={role === "ADMIN"} number="4" title="Профили доступа">{role === "ADMIN" ? <div className="employee-admin-access-note"><Icon name="warning" size={17} /><p>ADMIN получает все обычные capability организации. Профили доступа не назначаются и не должны создавать иллюзию ограничения его полного доступа. Защищённые governance-capability остаются только у OWNER.</p></div> : <div className="employee-create-profiles">{assignableProfiles.map((profile) => { const assignment = selected.get(profile.id); return <label className={assignment ? "selected" : ""} key={profile.id}><button type="button" aria-pressed={Boolean(assignment)} onClick={() => toggleProfile(profile)}><i>{assignment && <Icon name="check" size={11} />}</i><span><strong>{profile.name}</strong><small>{profile.description}</small></span></button>{assignment && <select aria-label={`Scope: ${profile.name}`} value={assignment.scopeType} onChange={(event) => changeScope(profile.id, event.target.value as ScopeType)}>{profile.allowedScopes.map((scope) => <option value={scope} key={scope}>{scope === "DEPARTMENT" ? "Отдел" : "Организация"}</option>)}</select>}</label>; })}<p>Без назначенных профилей сотрудник не получит рабочего доступа — только разрешённый self-service. Отсутствие доступа здесь является явным.</p></div>}</CreateStep>
      </div>
      <footer><span>{error || "Пароль первичного доступа отправится на email"}</span><div><button className="secondary-button" onClick={onClose}>Отмена</button><button className="primary-button" disabled={!canSubmit} onClick={submit}>{submitting ? "Создание" : "Создать сотрудника"}</button></div></footer>
    </aside>
  </>;
}

function CreateStep({ children, muted = false, number, title }: { children: ReactNode; muted?: boolean; number: string; title: string }) { return <section className={`employee-create-step ${muted ? "muted" : ""}`}><h3><i>{number}</i>{title}</h3>{children}</section>; }
function CreateField({ className = "", label, mono = false, onChange, placeholder, value }: { className?: string; label: string; mono?: boolean; onChange: (value: string) => void; placeholder: string; value: string }) { return <label className={`employee-create-field ${className}`}><span>{label}</span><input className={mono ? "mono" : ""} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} /></label>; }
function RoleOption({ active, description, label, onClick }: { active: boolean; description: string; label: string; onClick: () => void }) { return <button className={active ? "active" : ""} type="button" onClick={onClick}><i>{active && <span />}</i><span><strong>{label}</strong><small>{description}</small></span></button>; }

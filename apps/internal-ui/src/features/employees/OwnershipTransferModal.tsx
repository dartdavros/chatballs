import { useEffect, useMemo, useState } from "react";

import { api } from "../../api/client";
import { Icon } from "../../shared/icons";
import { Avatar } from "../../shared/ui";
import type { Employee, Role } from "../../types";

export function OwnershipTransferModal({ employees, onClose, open }: { employees: Employee[]; onClose: () => void; open: boolean }) {
  const owner = employees.find((employee) => employee.role === "OWNER") ?? null;
  const candidates = useMemo(() => employees.filter((employee) => employee.role !== "OWNER" && employee.isActive && !employee.isBlocked), [employees]);
  const [targetId, setTargetId] = useState<number | null>(null);
  const [previousOwnerRole, setPreviousOwnerRole] = useState<Extract<Role, "ADMIN" | "EMPLOYEE">>("ADMIN");
  const [confirmed, setConfirmed] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    setTargetId(candidates[0]?.id ?? null);
    setPreviousOwnerRole("ADMIN");
    setConfirmed(false);
    setError("");
  }, [candidates, open]);

  if (!open || !owner) return null;
  const target = candidates.find((employee) => employee.id === targetId) ?? null;

  async function transfer() {
    if (!confirmed || !target || sending) return;
    setSending(true); setError("");
    try {
      await api(`/api/v1/employees/${target.id}/transfer-ownership/`, {
        method: "POST",
        body: JSON.stringify({ previousOwnerRole }),
      });
      window.location.reload();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Ошибка передачи владения");
      setSending(false);
    }
  }

  return (
    <div className="ownership-modal-scrim" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="ownership-modal" role="dialog" aria-modal="true" aria-labelledby="ownership-title">
        <header><i><Icon name="split" size={21} /></i><div><h2 id="ownership-title">Передача владения</h2><p>Атомарная операция · в организации остаётся ровно один владелец</p></div></header>
        <div className="ownership-modal-body">
          <label className="ownership-select"><span>Новый владелец</span><select value={targetId ?? ""} onChange={(event) => setTargetId(Number(event.target.value))}>{candidates.map((employee) => <option value={employee.id} key={employee.id}>{employee.fullName} · {employee.role === "ADMIN" ? "Администратор" : "Сотрудник"} · {employee.positionTitle}</option>)}</select></label>
          {target && <div className="ownership-transition"><div><Avatar employee={owner} /><span><strong>{owner.fullName}</strong><small>Владелец</small></span></div><Icon name="arrow" size={20} /><div><Avatar employee={target} /><span><strong>{target.fullName}</strong><small>→ Владелец</small></span></div></div>}
          <span className="ownership-label">Новая роль прежнего владельца</span>
          <div className="ownership-role-options"><RoleOption active={previousOwnerRole === "ADMIN"} label="Администратор" onClick={() => setPreviousOwnerRole("ADMIN")} /><RoleOption active={previousOwnerRole === "EMPLOYEE"} label="Сотрудник" onClick={() => setPreviousOwnerRole("EMPLOYEE")} /></div>
          <div className="ownership-warning"><Icon name="warning" size={17} /><p>Новый владелец получит полный доступ и company placement. Вы потеряете права владельца, включая передачу владения и управление администраторами. Операция аудируется и необратима без повторной передачи.</p></div>
          <button className={`ownership-confirm ${confirmed ? "checked" : ""}`} type="button" onClick={() => setConfirmed((value) => !value)}><i>{confirmed && <Icon name="check" size={12} />}</i><span>Я понимаю последствия и подтверждаю передачу владения организацией.</span></button>
          {error && <p className="ownership-error">{error}</p>}
        </div>
        <footer><button className="secondary-button" type="button" onClick={onClose}>Отмена</button><button className="ownership-submit" type="button" disabled={!confirmed || !target || sending} onClick={transfer}>{sending ? "Передача" : "Передать владение"}</button></footer>
      </section>
    </div>
  );
}

function RoleOption({ active, label, onClick }: { active: boolean; label: string; onClick: () => void }) {
  return <button className={active ? "active" : ""} type="button" onClick={onClick}><i>{active && <span />}</i>{label}</button>;
}

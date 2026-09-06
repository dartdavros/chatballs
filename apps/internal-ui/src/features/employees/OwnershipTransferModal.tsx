import { useMemo, useState } from "react";

import { api } from "../../api/client";
import { Icon } from "../../shared/icons";
import { Avatar } from "../../shared/ui";
import type { Employee, Role } from "../../types";
import { employeeAvatarColor, roleBadge } from "./model";

// Передача владения (дизайн-базлайн v2, кадр E9). Кандидаты — только активные
// администраторы: чтобы передать сотруднику, его сначала делают админом.

const PREVIOUS_ROLES: Array<{ value: Extract<Role, "ADMIN" | "EMPLOYEE">; label: string }> = [
  { value: "ADMIN", label: "Администратор" },
  { value: "EMPLOYEE", label: "Сотрудник" },
];

export function OwnershipTransferModal({ employees, onClose }: { employees: Employee[]; onClose: () => void }) {
  const owner = employees.find((employee) => employee.role === "OWNER") ?? null;
  const candidates = useMemo(
    () => employees.filter((employee) => employee.role === "ADMIN" && employee.isActive && !employee.isBlocked),
    [employees],
  );
  const [targetId, setTargetId] = useState<number | null>(candidates[0]?.id ?? null);
  const [previousOwnerRole, setPreviousOwnerRole] = useState<Extract<Role, "ADMIN" | "EMPLOYEE">>("ADMIN");
  const [confirmed, setConfirmed] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  if (!owner) return null;
  const target = candidates.find((employee) => employee.id === targetId) ?? null;

  async function transfer() {
    if (!confirmed || !target || sending) return;
    setSending(true);
    setError("");
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
    <div className="employee-dialog-scrim">
      <section className="employee-transfer-dialog" role="dialog" aria-label="Передача владения">
        <header>
          <i><Icon name="transfer" size={21} strokeWidth={1.9} /></i>
          <div>
            <h2>Передача владения</h2>
            <p>Атомарная операция · в организации остаётся ровно один владелец</p>
          </div>
        </header>

        <div className="employee-transfer-body">
          {candidates.length === 0 ? (
            <p className="employee-create-note">Активных администраторов нет. Чтобы передать владение сотруднику, сначала сделайте его администратором.</p>
          ) : (
            <>
              <label className="employee-field is-single">
                <span>Новый владелец · только администраторы</span>
                <span className="employee-transfer-select">
                  <select value={targetId === null ? "" : String(targetId)} onChange={(event) => setTargetId(Number(event.target.value))}>
                    {candidates.map((employee) => (
                      <option value={employee.id} key={employee.id}>
                        {employee.fullName || employee.email} · {roleBadge(employee.role).text} · {employee.positionTitle}
                      </option>
                    ))}
                  </select>
                  <Icon name="chevron" size={14} strokeWidth={1.8} />
                </span>
                <small className="employee-transfer-note">В списке только активные администраторы. Чтобы передать владение сотруднику, сначала сделайте его администратором.</small>
              </label>

              <div className="employee-transfer-pair">
                <div>
                  <Avatar employee={owner} background={employeeAvatarColor(owner)} />
                  <span>
                    <strong>{owner.fullName || owner.email}</strong>
                    <small>Владелец</small>
                  </span>
                </div>
                <Icon name="arrow" size={20} strokeWidth={1.8} />
                <div>
                  {target && <Avatar employee={target} background={employeeAvatarColor(target)} />}
                  <span>
                    <strong>{target?.fullName || target?.email}</strong>
                    <small className="is-accent">→ Владелец</small>
                  </span>
                </div>
              </div>

              <div className="employee-transfer-role">
                <span>Новая роль прежнего владельца</span>
                <div>
                  {PREVIOUS_ROLES.map((option) => (
                    <button
                      className={`employee-transfer-role-option ${previousOwnerRole === option.value ? "is-on" : ""}`}
                      type="button"
                      onClick={() => setPreviousOwnerRole(option.value)}
                      key={option.value}
                    >
                      <i>{previousOwnerRole === option.value && <span />}</i>
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="employee-password-warning">
                <Icon name="warning" size={17} strokeWidth={1.9} />
                <p>Новый владелец получит полный доступ. Вы потеряете права владельца, включая передачу владения и управление администраторами. Операция аудируется и необратима без повторной передачи.</p>
              </div>

              <button className="employee-transfer-confirm" type="button" aria-pressed={confirmed} onClick={() => setConfirmed((value) => !value)}>
                <i>{confirmed && <Icon name="check" size={12} strokeWidth={3} />}</i>
                <span>Я понимаю последствия и подтверждаю передачу владения организацией.</span>
              </button>

              {error && <div className="employees-error"><Icon name="alert" size={16} strokeWidth={1.8} />{error}</div>}
            </>
          )}
        </div>

        <footer>
          <button className="secondary-button" type="button" onClick={onClose}>Отмена</button>
          <button className="employee-transfer-submit" type="button" disabled={!confirmed || !target || sending} onClick={() => void transfer()}>
            {sending ? "Передача…" : "Передать владение"}
          </button>
        </footer>
      </section>
    </div>
  );
}

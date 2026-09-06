import { useCallback, useEffect, useState } from "react";

import { api } from "../../api/client";
import { Icon } from "../../shared/icons";
import type { Employee, EmployeeGroup, RouteKey } from "../../types";
import { blockEmployee, resetEmployeePassword, terminateEmployeeSessions, type IssuedPassword } from "./api";
import { EmployeeDetailHeader } from "./EmployeeDetailHeader";
import { EmployeeDetailRail } from "./EmployeeDetailRail";
import { EmployeeIdentitySections } from "./EmployeeIdentitySections";
import { EmployeePasswordDialog } from "./EmployeePasswordDialog";
import { EmployeeSecuritySections } from "./EmployeeSecuritySections";
import { OwnershipTransferModal } from "./OwnershipTransferModal";
import { employeeForm, employeeStatusKey, type EmployeeForm } from "./model";

// Карточка сотрудника (дизайн-базлайн v2, кадры E3/E4).

export function EmployeeDetailPage({ groups, employee, employees, reload, setRoute }: {
  groups: EmployeeGroup[];
  employee: Employee;
  employees: Employee[];
  reload: () => void;
  setRoute: (route: RouteKey) => void;
}) {
  const [currentEmployee, setCurrentEmployee] = useState(employee);
  const [form, setForm] = useState<EmployeeForm>(() => employeeForm(employee));
  const [saving, setSaving] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [issued, setIssued] = useState<IssuedPassword | null>(null);
  const [transferOpen, setTransferOpen] = useState(false);
  const status = employeeStatusKey(currentEmployee);

  const refresh = useCallback(async () => {
    const payload = await api<{ employee: Employee }>(`/api/v1/employees/${employee.id}/`);
    setCurrentEmployee(payload.employee);
    setForm(employeeForm(payload.employee));
  }, [employee.id]);

  useEffect(() => { void refresh().catch(() => undefined); }, [refresh]);
  useEffect(() => { setCurrentEmployee(employee); setForm(employeeForm(employee)); setMessage(""); }, [employee]);

  function updateForm(field: keyof EmployeeForm, value: string | boolean | number[]) {
    setForm((current) => ({ ...current, [field]: value }));
    setMessage("");
  }

  async function saveEmployee() {
    setSaving(true);
    setMessage("");
    try {
      await api(`/api/v1/employees/${currentEmployee.id}/update/`, { method: "POST", body: JSON.stringify(form) });
      await refresh();
      reload();
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Не удалось сохранить изменения");
    } finally {
      setSaving(false);
    }
  }

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setMessage("");
    try {
      await action();
      await refresh();
      reload();
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Не удалось выполнить действие");
    } finally {
      setBusy(false);
    }
  }

  // Кадр E4: на карточке владельца всегда стоит напоминание о правиле роли —
  // сменить её можно только передачей владения.
  const isOwnerCard = currentEmployee.role === "OWNER";

  return (
    <div className="employee-page">
      <EmployeeDetailHeader employee={currentEmployee} form={form} saveEmployee={() => void saveEmployee()} saving={saving} setRoute={setRoute} />

      {isOwnerCard && (
        <div className="employee-owner-banner">
          <Icon name="lock" size={16} strokeWidth={1.8} />
          <span>Владельца нельзя удалить, заблокировать или сменить ему роль — единственный путь изменения роли владельца это передача владения.</span>
        </div>
      )}
      {message && <div className="employees-error"><Icon name="alert" size={16} strokeWidth={1.8} />{message}</div>}

      <div className="employee-grid">
        <div className="employee-column">
          <EmployeeIdentitySections groups={groups} employee={currentEmployee} form={form} updateForm={updateForm} />
          <EmployeeSecuritySections
            blocked={status === "blocked"}
            busy={busy}
            employee={currentEmployee}
            form={form}
            updateForm={updateForm}
            onResetPassword={() => void run(async () => { setIssued(await resetEmployeePassword(currentEmployee.id, "show")); })}
            onTerminateSessions={() => void run(() => terminateEmployeeSessions(currentEmployee.id))}
            onToggleBlock={() => void run(() => blockEmployee(currentEmployee.id, !currentEmployee.isBlocked))}
            onTransferOwnership={() => setTransferOpen(true)}
          />
        </div>
        <EmployeeDetailRail employee={currentEmployee} />
      </div>

      {issued && <EmployeePasswordDialog issued={issued} onClose={() => setIssued(null)} />}
      {transferOpen && <OwnershipTransferModal employees={employees} onClose={() => setTransferOpen(false)} />}
    </div>
  );
}

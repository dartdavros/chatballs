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

// Карточка грузится по идентификатору: список сотрудников постраничный, и
// открытый по ссылке человек может быть не на загруженной странице.
export function EmployeeDetailPage({ groups, employeeId, setRoute }: {
  groups: EmployeeGroup[];
  employeeId: number;
  setRoute: (route: RouteKey) => void;
}) {
  const [currentEmployee, setCurrentEmployee] = useState<Employee | null>(null);
  const [form, setForm] = useState<EmployeeForm | null>(null);
  const [saving, setSaving] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [issued, setIssued] = useState<IssuedPassword | null>(null);
  const [transferOpen, setTransferOpen] = useState(false);

  const refresh = useCallback(async () => {
    const payload = await api<{ employee: Employee }>(`/api/v1/employees/${employeeId}/`);
    setCurrentEmployee(payload.employee);
    setForm(employeeForm(payload.employee));
  }, [employeeId]);

  useEffect(() => {
    setMessage("");
    void refresh().catch(() => setMessage("Не удалось загрузить карточку сотрудника"));
  }, [refresh]);

  function updateForm(field: keyof EmployeeForm, value: string | boolean | number[]) {
    setForm((current) => (current ? { ...current, [field]: value } : current));
    setMessage("");
  }

  async function saveEmployee() {
    setSaving(true);
    setMessage("");
    try {
      await api(`/api/v1/employees/${employeeId}/update/`, { method: "POST", body: JSON.stringify(form) });
      await refresh();
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
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Не удалось выполнить действие");
    } finally {
      setBusy(false);
    }
  }

  if (!currentEmployee || !form) {
    return (
      <div className="employee-page">
        {message && <div className="employees-error"><Icon name="alert" size={16} strokeWidth={1.8} />{message}</div>}
      </div>
    );
  }
  const status = employeeStatusKey(currentEmployee);
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
      {transferOpen && <OwnershipTransferModal onClose={() => setTransferOpen(false)} />}
    </div>
  );
}

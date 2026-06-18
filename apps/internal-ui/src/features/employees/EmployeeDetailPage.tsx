import { useEffect, useState } from "react";

import { api } from "../../api/client";
import type { Employee, RouteKey } from "../../types";
import { EmployeeDetailHeader } from "./EmployeeDetailHeader";
import { EmployeeDetailRail } from "./EmployeeDetailRail";
import { EmployeeDetailSections } from "./EmployeeDetailSections";
import { employeeDetails, employeeForm, employeeStatusKey, type EmployeeForm } from "./model";

export function EmployeeDetailPage({ employee, reload, setRoute }: { employee: Employee; reload: () => void; setRoute: (route: RouteKey) => void }) {
  const [currentEmployee, setCurrentEmployee] = useState(employee);
  const [form, setForm] = useState<EmployeeForm>(() => employeeForm(employee));
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const details = employeeDetails(currentEmployee);
  const status = employeeStatusKey(currentEmployee);
  const blocked = status === "blocked";

  useEffect(() => {
    setCurrentEmployee(employee);
    setForm(employeeForm(employee));
    setMessage("");
  }, [employee]);

  function updateForm(field: keyof EmployeeForm, value: string | boolean) {
    setForm((current) => ({ ...current, [field]: value }));
    setMessage("");
  }

  async function saveEmployee() {
    setSaving(true);
    setMessage("");
    try {
      const payload = await api<{ employee: Employee }>(`/api/v1/employees/${currentEmployee.id}/update/`, {
        method: "POST",
        body: JSON.stringify(form),
      });
      setCurrentEmployee(payload.employee);
      setMessage("Изменения сохранены");
      reload();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Не удалось сохранить изменения");
    } finally {
      setSaving(false);
    }
  }

  async function resetPassword() {
    setMessage("");
    const payload = await api<{ employee: Employee; temporaryPassword: string }>(`/api/v1/employees/${currentEmployee.id}/reset-password/`, { method: "POST" });
    setCurrentEmployee(payload.employee);
    setMessage(`Временный пароль: ${payload.temporaryPassword}`);
    reload();
  }

  async function revokeSessions() {
    const payload = await api<{ employee: Employee; revoked: number }>(`/api/v1/employees/${currentEmployee.id}/revoke-sessions/`, { method: "POST" });
    setCurrentEmployee(payload.employee);
    setMessage(`Сессии завершены: ${payload.revoked}`);
  }

  async function toggleBlocked() {
    const action = blocked ? "unblock" : "block";
    const payload = await api<{ employee: Employee }>(`/api/v1/employees/${currentEmployee.id}/${action}/`, { method: "POST" });
    setCurrentEmployee(payload.employee);
    setMessage(blocked ? "Сотрудник разблокирован" : "Сотрудник заблокирован");
    reload();
  }

  return (
    <>
      <EmployeeDetailHeader employee={employee} departmentLabel={details.departmentLabel} form={form} saveEmployee={saveEmployee} saving={saving} setRoute={setRoute} status={status} />
      {message && <div className="employee-action-message">{message}</div>}
      <div className="employee-detail-grid">
        <EmployeeDetailSections
          blocked={blocked}
          currentEmployee={currentEmployee}
          details={details}
          form={form}
          resetPassword={resetPassword}
          revokeSessions={revokeSessions}
          toggleBlocked={toggleBlocked}
          updateForm={updateForm}
        />
        <EmployeeDetailRail details={details} status={status} />
      </div>
    </>
  );
}

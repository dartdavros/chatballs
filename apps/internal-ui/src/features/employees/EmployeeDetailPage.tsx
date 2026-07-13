import { useCallback, useEffect, useState } from "react";

import { api } from "../../api/client";
import type { Department, Employee, RouteKey, SessionUser } from "../../types";
import { EmployeeDetailHeader } from "./EmployeeDetailHeader";
import { EmployeeDetailRail } from "./EmployeeDetailRail";
import { EmployeeDetailSections } from "./EmployeeDetailSections";
import { employeeForm, employeeStatusKey, type EmployeeForm } from "./model";

export function EmployeeDetailPage({ departments, employee, reload, setRoute, user }: {
  departments: Department[];
  employee: Employee;
  reload: () => void;
  setRoute: (route: RouteKey) => void;
  user: SessionUser;
}) {
  const [currentEmployee, setCurrentEmployee] = useState(employee);
  const [form, setForm] = useState<EmployeeForm>(() => employeeForm(employee));
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const status = employeeStatusKey(currentEmployee);

  const refresh = useCallback(async () => {
    const payload = await api<{ employee: Employee }>(`/api/v1/employees/${employee.id}/`);
    setCurrentEmployee(payload.employee);
    setForm(employeeForm(payload.employee));
  }, [employee.id]);

  useEffect(() => { void refresh().catch(() => undefined); }, [refresh]);
  useEffect(() => { setCurrentEmployee(employee); setForm(employeeForm(employee)); setMessage(""); }, [employee]);

  function updateForm(field: keyof EmployeeForm, value: string | boolean) {
    setForm((current) => ({ ...current, [field]: value }));
    setMessage("");
  }

  async function saveEmployee() {
    setSaving(true); setMessage("");
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

  const readOnlyPrivileged = user.role === "ADMIN" && (currentEmployee.role === "ADMIN" || currentEmployee.role === "OWNER") && !currentEmployee.permissions?.canUpdateProfile;
  return <div className="employee-detail-page">
    <EmployeeDetailHeader departments={departments} employee={currentEmployee} form={form} saveEmployee={saveEmployee} saving={saving} setRoute={setRoute} status={status} />
    {readOnlyPrivileged && <div className="employee-readonly-banner">Привилегированная учётная запись ({currentEmployee.role}). Администратор не может изменять данные, роль, размещение, доступ и security state, блокировать, сбрасывать пароль или завершать сессии этого сотрудника. Эти операции выполняет только владелец.</div>}
    {message && <div className="employee-action-message">{message}</div>}
    <div className="employee-detail-grid"><EmployeeDetailSections blocked={status === "blocked"} departments={departments} employee={currentEmployee} form={form} updateForm={updateForm} /><EmployeeDetailRail employee={currentEmployee} /></div>
  </div>;
}

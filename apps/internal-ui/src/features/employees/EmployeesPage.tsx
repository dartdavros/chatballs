import { useEffect, useState } from "react";
import type { ReactNode } from "react";

import { api } from "../../api/client";
import type { Employee, Role, RouteKey } from "../../types";
import { Icon } from "../../shared/icons";
import { Avatar, EmptyState, PageHeader, RoleBadge, Segmented, StatusPill } from "../../shared/ui";

export function EmployeesPage({ employees, reload, openEmployee }: { employees: Employee[]; reload: () => void; openEmployee: (employee: Employee) => void }) {
  const [role, setRole] = useState<"all" | Role>("all");
  const [status, setStatus] = useState<"all" | "active" | "invited" | "blocked">("all");
  const [query, setQuery] = useState("");
  const [menuId, setMenuId] = useState<number | null>(null);
  const filtered = employees.filter((employee) => {
    const employeeStatus = employeeStatusKey(employee);
    const q = query.trim().toLowerCase();
    return (
      (role === "all" || employee.role === role) &&
      (status === "all" || employeeStatus === status) &&
      (!q || employee.fullName.toLowerCase().includes(q) || employee.email.toLowerCase().includes(q))
    );
  });
  async function block(employee: Employee) {
    if (employee.role === "OWNER" || employee.isBlocked) return;
    await api(`/api/v1/employees/${employee.id}/block/`, { method: "POST" });
    setMenuId(null);
    reload();
  }
  const resetFilters = () => {
    setQuery("");
    setRole("all");
    setStatus("all");
    setMenuId(null);
  };
  return (
    <>
      {menuId !== null && <button className="menu-scrim" aria-label="Закрыть меню" onClick={() => setMenuId(null)} />}
      <PageHeader
        title="Сотрудники"
        text={<>Доступ к Hub · показано <b>{filtered.length}</b> из {employees.length}</>}
        action={<button className="primary-button" type="button"><Icon name="team" size={16} />Добавить оператора</button>}
      />
      <div className="filter-bar employees-filter">
        <label className="employee-search">
          <Icon name="search" size={15} />
          <input value={query} onChange={(event) => { setQuery(event.target.value); setMenuId(null); }} placeholder="Поиск по имени или email…" />
        </label>
        <div className="filter-group">
          <span>Роль</span>
          <Segmented value={role} setValue={(nextRole) => { setRole(nextRole); setMenuId(null); }} items={[["all", "Все"], ["OWNER", "OWNER"], ["OPERATOR", "OPERATOR"]]} />
        </div>
        <div className="filter-group">
          <span>Статус</span>
          <Segmented value={status} setValue={(nextStatus) => { setStatus(nextStatus); setMenuId(null); }} items={[["all", "Все"], ["active", "Активные"], ["invited", "Приглашённые"], ["blocked", "Заблокированные"]]} />
        </div>
        <button className="reset-filter" type="button" onClick={resetFilters}>Сбросить</button>
      </div>
      <div className="table-card employees-card">
        <div className="table-scroll">
          <table className="baseline-table employees-table">
            <thead><tr><th>СОТРУДНИК</th><th>РОЛЬ</th><th>ОТДЕЛ</th><th>СТАТУС</th><th>ПОСЛЕДНИЙ ВХОД</th><th className="numeric">ДИАЛОГИ</th><th /></tr></thead>
            <tbody>
              {filtered.map((employee) => <EmployeeRow employee={employee} block={block} openEmployee={openEmployee} menuId={menuId} setMenuId={setMenuId} key={employee.id} />)}
            </tbody>
          </table>
        </div>
        {!filtered.length && <EmptyState title="Сотрудники не найдены" />}
        <div className="employees-footer">
          <span>Показано {filtered.length} из {employees.length}</span>
          <span>Сессии и пароли управляются в карточке сотрудника</span>
        </div>
      </div>
    </>
  );
}

function employeeStatusKey(employee: Employee): "active" | "invited" | "blocked" {
  if (employee.isBlocked) return "blocked";
  if (employee.mustChangePassword) return "invited";
  return "active";
}

function EmployeeRow({ employee, block, openEmployee, menuId, setMenuId }: { employee: Employee; block: (employee: Employee) => void; openEmployee: (employee: Employee) => void; menuId: number | null; setMenuId: (id: number | null) => void }) {
  const details = employeeDetails(employee);
  const dialogs = String(details.workload.activeDialogs);
  const status = employeeStatusKey(employee);
  const menuOpen = menuId === employee.id;
  const open = () => {
    setMenuId(null);
    openEmployee(employee);
  };
  return (
    <tr>
      <td><div className="person-cell"><Avatar employee={employee} /><button className="person-link" type="button" onClick={open}><strong>{employee.fullName || employee.email}</strong><small>{employee.email}</small></button></div></td>
      <td><RoleBadge role={employee.role} /></td>
      <td>{employee.department === "sales" ? "Продажи" : "—"}</td>
      <td><StatusPill status={status} /></td>
      <td>{details.account.lastLogin}</td>
      <td className={`numeric ${dialogs === "0" ? "muted-number" : ""}`}>{dialogs}</td>
      <td className="row-actions">
        <button className="row-menu-button" aria-label="Действия сотрудника" onClick={() => setMenuId(menuOpen ? null : employee.id)}><Icon name="more" /></button>
        {menuOpen && (
          <div className="row-menu">
            <button type="button" onClick={open}><Icon name="external" size={15} />Открыть карточку</button>
            <a href="#" onClick={(event) => event.preventDefault()}><Icon name="logout" size={15} />Завершить сессии</a>
            <a href="#" onClick={(event) => event.preventDefault()}><Icon name="key" size={15} />Сбросить пароль</a>
            <span />
            <button className={employee.isBlocked ? "success" : "danger"} onClick={() => block(employee)} disabled={employee.role === "OWNER" || employee.isBlocked}>{employee.isBlocked ? "Разблокировать" : "Заблокировать"}</button>
          </div>
        )}
      </td>
    </tr>
  );
}

export function EmployeeDetailPage({ employee, reload, setRoute }: { employee: Employee; reload: () => void; setRoute: (route: RouteKey) => void }) {
  const [currentEmployee, setCurrentEmployee] = useState(employee);
  const [form, setForm] = useState({
    fullName: employee.fullName || employee.email,
    phone: employee.phone || employeeDetails(employee).phone,
    email: employee.email,
    role: employee.role,
    department: employee.department ?? "sales",
    totpEnabled: employee.totpEnabled,
  });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const details = employeeDetails(currentEmployee);
  const status = employeeStatusKey(currentEmployee);
  const blocked = status === "blocked";
  useEffect(() => {
    setCurrentEmployee(employee);
    setForm({
      fullName: employee.fullName || employee.email,
      phone: employee.phone || employeeDetails(employee).phone,
      email: employee.email,
      role: employee.role,
      department: employee.department ?? "sales",
      totpEnabled: employee.totpEnabled,
    });
    setMessage("");
  }, [employee]);
  const updateForm = (field: keyof typeof form, value: string | boolean) => {
    setForm((current) => ({ ...current, [field]: value }));
    setMessage("");
  };
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
      <section className="employee-detail-header">
        <div className="employee-detail-main">
          <Avatar employee={employee} />
          <div className="employee-title">
            <div>
              <h1>{form.fullName || form.email}</h1>
              <RoleBadge role={form.role} />
              <StatusPill status={status} />
            </div>
            <p>{form.email} · {details.departmentLabel}</p>
          </div>
        </div>
        <div className="employee-header-actions">
          <button className="secondary-button" type="button" onClick={() => setRoute("employees")}>Отмена</button>
          <button className="primary-button" type="button" onClick={saveEmployee} disabled={saving}><Icon name="save" size={15} />{saving ? "Сохранение" : "Сохранить"}</button>
        </div>
      </section>
      {message && <div className="employee-action-message">{message}</div>}

      <div className="employee-detail-grid">
        <div className="employee-detail-left">
          <section className="employee-detail-card">
            <h3>Основные данные</h3>
            <div className="employee-form-grid">
              <EditableField label="Имя" value={form.fullName} onChange={(value) => updateForm("fullName", value)} />
              <EditableField label="Телефон" value={form.phone} onChange={(value) => updateForm("phone", value)} />
              <EditableField label="Email · используется для входа" value={form.email} onChange={(value) => updateForm("email", value)} mono wide />
            </div>
          </section>

          <section className="employee-detail-card">
            <h3>Роль и доступ</h3>
            <div className="employee-form-grid">
              <SelectLike label="Роль" value={form.role} onChange={(value) => updateForm("role", value)} options={[["OPERATOR", "OPERATOR"], ["OWNER", "OWNER"]]} />
              <SelectLike label="Отдел" value={form.department} onChange={(value) => updateForm("department", value)} options={[["sales", "Отдел продаж"]]} />
            </div>
            <label className="employee-access-label">Доступные разделы</label>
            <div className="employee-access-list">
              <span className="allowed"><Icon name="check" size={12} />Диалоги</span>
              <span className="allowed"><Icon name="check" size={12} />Клиенты</span>
              <span className="allowed"><Icon name="check" size={12} />Заказы · чтение</span>
              <span>Финансы · нет</span>
              <span>Настройки · нет</span>
            </div>
          </section>

          <section className="employee-detail-card">
            <h3>Безопасность</h3>
            <div className="security-row">
              <div><strong>Пароль</strong><span>Последняя смена: {details.security.passwordChangedAt}</span></div>
              <button className="secondary-button" type="button" onClick={resetPassword}>Сбросить пароль</button>
            </div>
            <div className="security-row">
              <div><strong>Двухфакторная аутентификация (TOTP)</strong><span>{form.totpEnabled ? "Включена · требуется при каждом входе" : "Отключена для этого сотрудника"}</span></div>
              <button className={`detail-totp-switch ${form.totpEnabled ? "on" : ""}`} type="button" aria-label="Переключить TOTP" onClick={() => updateForm("totpEnabled", !form.totpEnabled)}><i /></button>
            </div>
            <div className="security-row last">
              <div><strong>Активные сессии</strong><span>{details.security.sessions}</span></div>
              <button className="secondary-button" type="button" onClick={revokeSessions}>Завершить все</button>
            </div>
          </section>

          <section className="employee-danger-card">
            <h3>Опасная зона</h3>
            <div>
              <p>{blocked ? "Сотрудник заблокирован и не может войти. Разблокировка восстановит доступ к разделам отдела." : "Блокировка немедленно завершит все сессии и закроет доступ. Активные диалоги вернутся в очередь. Действие требует подтверждения."}</p>
              <button type="button" onClick={toggleBlocked} disabled={currentEmployee.role === "OWNER"}>{blocked ? "Разблокировать сотрудника" : "Заблокировать сотрудника"}</button>
            </div>
          </section>
        </div>

        <aside className="employee-detail-rail">
          <section className="employee-detail-card compact">
            <h3>Статус аккаунта</h3>
            <KeyValue label="Статус" value={<StatusPill status={status} />} />
            <KeyValue label="Создан" value={details.account.createdAt} />
            <KeyValue label="Приглашение принято" value={details.account.inviteAcceptedAt} />
            <KeyValue label="Последний вход" value={details.account.lastLogin} />
          </section>

          <section className="employee-detail-card compact">
            <h3>Текущая нагрузка</h3>
            <div className="workload-grid">
              <MetricBox label="Активные диалоги" value={details.workload.activeDialogs} />
              <MetricBox label="В очереди" value={details.workload.queue} />
              <MetricBox label="Продажи · сегодня" value={details.workload.salesToday} />
              <MetricBox label="Ср. ответ" value={details.workload.avgReply} />
            </div>
          </section>

          <section className="employee-detail-card compact">
            <h3>Последние действия</h3>
            <div className="employee-activity-list">
              {details.activity.map((item) => (
                <div key={item.text}>
                  <span style={{ background: item.dot }} />
                  <p><strong>{item.text}</strong><small>{item.time}</small></p>
                </div>
              ))}
            </div>
          </section>
        </aside>
      </div>
    </>
  );
}

function EditableField({ label, value, onChange, mono = false, wide = false }: { label: string; value: string; onChange: (value: string) => void; mono?: boolean; wide?: boolean }) {
  return <label className={`readonly-field ${wide ? "wide" : ""}`}><span>{label}</span><input className={mono ? "mono" : ""} value={value} onChange={(event) => onChange(event.target.value)} /></label>;
}

function SelectLike({ label, value, onChange, options }: { label: string; value: string; onChange: (value: string) => void; options: Array<[string, string]> }) {
  return (
    <label className="readonly-field select-like">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map(([optionValue, labelText]) => <option value={optionValue} key={optionValue}>{labelText}</option>)}
      </select>
      <Icon name="chevron" size={14} />
    </label>
  );
}

function KeyValue({ label, value }: { label: string; value: ReactNode }) {
  return <div className="key-value"><span>{label}</span><strong>{value}</strong></div>;
}

function MetricBox({ label, value }: { label: string; value: ReactNode }) {
  return <div><span>{label}</span><strong>{value}</strong></div>;
}

function employeeDetails(employee: Employee) {
  if (employee.email === "a.kotova@edevs.tech") {
    return {
      phone: employee.phone || "+7 916 245 14 02",
      departmentLabel: employee.department === "sales" ? "Отдел продаж" : "—",
      account: {
        createdAt: "12 мая 2026",
        inviteAcceptedAt: "12 мая 2026",
        lastLogin: "5 мин назад",
      },
      security: {
        passwordChangedAt: "28 мая 2026",
        sessions: "2 устройства · Chrome (Москва), Safari (Москва)",
      },
      workload: {
        activeDialogs: 3,
        queue: 0,
        salesToday: 5,
        avgReply: "1м 40с",
      },
      activity: [
        { dot: "#52c41a", text: "Закрыла диалог · продажа Foxray", time: "8 мин назад" },
        { dot: "#1677ff", text: "Забрала диалог из очереди", time: "22 мин назад" },
        { dot: "#bfbfbf", text: "Вход в систему · Chrome", time: "сегодня 09:02" },
      ],
    };
  }
  return {
    phone: "",
    departmentLabel: employee.department === "sales" ? "Отдел продаж" : "—",
    account: {
      createdAt: "—",
      inviteAcceptedAt: employee.mustChangePassword ? "—" : "—",
      lastLogin: employee.role === "OWNER" ? "сейчас · онлайн" : "не входил",
    },
    security: {
      passwordChangedAt: "—",
      sessions: employee.role === "OWNER" ? "1 устройство · текущий браузер" : "—",
    },
    workload: {
      activeDialogs: 0,
      queue: 0,
      salesToday: 0,
      avgReply: "—",
    },
    activity: [
      { dot: "#bfbfbf", text: "Активность не зафиксирована", time: "—" },
    ],
  };
}

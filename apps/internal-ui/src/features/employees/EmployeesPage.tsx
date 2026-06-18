import { useState } from "react";
import type { ReactNode } from "react";

import { api } from "../../api/client";
import type { Employee, Role, RouteKey } from "../../types";
import { Icon } from "../../shared/icons";
import { Avatar, EmptyState, PageHeader, ReadOnlyField, RoleBadge, Segmented, StatusPill } from "../../shared/ui";

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

export function EmployeeDetailPage({ employee, setRoute }: { employee: Employee; setRoute: (route: RouteKey) => void }) {
  const [totpEnabled, setTotpEnabled] = useState(employee.totpEnabled);
  const details = employeeDetails(employee);
  const status = employeeStatusKey(employee);
  const blocked = status === "blocked";
  return (
    <>
      <section className="employee-detail-header">
        <div className="employee-detail-main">
          <Avatar employee={employee} />
          <div className="employee-title">
            <div>
              <h1>{employee.fullName || employee.email}</h1>
              <RoleBadge role={employee.role} />
              <StatusPill status={status} />
            </div>
            <p>{employee.email} · {details.departmentLabel}</p>
          </div>
        </div>
        <div className="employee-header-actions">
          <button className="secondary-button" type="button" onClick={() => setRoute("employees")}>Отмена</button>
          <button className="primary-button" type="button"><Icon name="save" size={15} />Сохранить</button>
        </div>
      </section>

      <div className="employee-detail-grid">
        <div className="employee-detail-left">
          <section className="employee-detail-card">
            <h3>Основные данные</h3>
            <div className="employee-form-grid">
              <ReadOnlyField label="Имя" value={employee.fullName || employee.email} editable />
              <ReadOnlyField label="Телефон" value={details.phone} editable />
              <ReadOnlyField label="Email · используется для входа" value={employee.email} editable mono wide />
            </div>
          </section>

          <section className="employee-detail-card">
            <h3>Роль и доступ</h3>
            <div className="employee-form-grid">
              <SelectLike label="Роль" value={employee.role} />
              <SelectLike label="Отдел" value={details.departmentLabel} />
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
              <button className="secondary-button" type="button">Сбросить пароль</button>
            </div>
            <div className="security-row">
              <div><strong>Двухфакторная аутентификация (TOTP)</strong><span>{totpEnabled ? "Включена · требуется при каждом входе" : "Отключена для этого сотрудника"}</span></div>
              <button className={`detail-totp-switch ${totpEnabled ? "on" : ""}`} type="button" aria-label="Переключить TOTP" onClick={() => setTotpEnabled((value) => !value)}><i /></button>
            </div>
            <div className="security-row last">
              <div><strong>Активные сессии</strong><span>{details.security.sessions}</span></div>
              <button className="secondary-button" type="button">Завершить все</button>
            </div>
          </section>

          <section className="employee-danger-card">
            <h3>Опасная зона</h3>
            <div>
              <p>{blocked ? "Сотрудник заблокирован и не может войти. Разблокировка восстановит доступ к разделам отдела." : "Блокировка немедленно завершит все сессии и закроет доступ. Активные диалоги вернутся в очередь. Действие требует подтверждения."}</p>
              <button type="button">{blocked ? "Разблокировать сотрудника" : "Заблокировать сотрудника"}</button>
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

function SelectLike({ label, value }: { label: string; value: string }) {
  return (
    <label className="readonly-field select-like">
      <span>{label}</span>
      <input value={value} readOnly />
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
      phone: "+7 916 245 14 02",
      departmentLabel: "Отдел продаж",
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

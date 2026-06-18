import { routes } from "../routes";
import type { AppData, Employee, RouteKey, SessionUser } from "../types";
import { CommandCenter, commandCenterModel } from "../features/command/CommandCenter";
import { DepartmentsPage } from "../features/departments/DepartmentsPage";
import { EmployeeDetailPage, EmployeesPage } from "../features/employees/EmployeesPage";
import { ProductsPage } from "../features/products/ProductsPage";
import { ProfilePage } from "../features/profile/ProfilePage";
import { SalesOverviewPage } from "../features/sales/SalesOverviewPage";
import { Avatar } from "../shared/ui";
import { Icon, PulseIcon } from "../shared/icons";

function Sidebar({ route, user, setRoute }: { route: RouteKey; user: SessionUser; setRoute: (route: RouteKey) => void }) {
  const nav = [
    { key: "command" as const, label: "Командный центр", icon: "grid" as const },
    { label: "КОМПАНИЯ", group: true },
    { key: "departments" as const, label: "Отделы", icon: "building" as const },
    { key: "employees" as const, label: "Сотрудники", icon: "team" as const },
    { key: "products" as const, label: "Продукты", icon: "box" as const },
    { label: "ПЛАТФОРМА", group: true },
    { label: "AI", icon: "robot" as const, disabled: true },
    { label: "Интеграции", icon: "plug" as const, disabled: true },
    { divider: true },
    { label: "Настройки", icon: "settings" as const, disabled: true },
  ];
  return (
    <aside className="hub-sidebar">
      <button className="hub-brand" type="button" onClick={() => setRoute("command")}>
        <div className="hub-brand-mark"><PulseIcon /></div>
        <div><strong>Edevs Hub</strong><span>Уровень компании</span></div>
      </button>
      <nav className="hub-nav">
        {nav.map((item, index) => {
          if ("group" in item) return <div className="hub-nav-group" key={item.label}>{item.label}</div>;
          if ("divider" in item) return <div className="hub-nav-divider" key={index} />;
          const nextRoute = "key" in item ? item.key : null;
          const active = nextRoute === route || (nextRoute === "employees" && route === "employeeDetail");
          return (
            <button className={`hub-nav-item ${active ? "is-active" : ""}`} disabled={item.disabled} key={item.label} onClick={() => nextRoute && setRoute(nextRoute)}>
              {active && <span className="active-bar" />}
              <Icon name={item.icon} />
              {item.label}
            </button>
          );
        })}
      </nav>
      <button className={`profile-link ${route === "profile" ? "is-active" : ""}`} onClick={() => setRoute("profile")}>
        <Avatar user={user} />
        <span><strong>{user.fullName || user.email}</strong><small>{user.role}</small></span>
      </button>
    </aside>
  );
}

function SalesSidebar({ user, setRoute }: { user: SessionUser; setRoute: (route: RouteKey) => void }) {
  const nav = [
    { label: "Обзор", icon: "grid" as const, active: true },
    { label: "Диалоги", icon: "bell" as const, badge: "2" },
    { label: "Клиенты", icon: "team" as const },
    { label: "Продажи", icon: "box" as const },
  ];
  return (
    <aside className="hub-sidebar sales-workspace-sidebar">
      <div className="sales-sidebar-back-wrap">
        <button className="sales-sidebar-back" type="button" onClick={() => setRoute("command")}><Icon name="arrow" size={16} />Назад в Hub</button>
      </div>
      <div className="sales-sidebar-title">
        <div className="sales-sidebar-icon"><Icon name="shop" size={19} /></div>
        <div><strong>Продажи</strong><span>Рабочее пространство</span></div>
      </div>
      <nav className="hub-nav sales-workspace-nav">
        {nav.map((item) => (
          <button className={`hub-nav-item ${item.active ? "is-active" : ""}`} type="button" onClick={() => item.active && setRoute("salesOverview")} key={item.label}>
            {item.active && <span className="active-bar" />}
            <Icon name={item.icon} />
            {item.label}
            {item.badge && <b>{item.badge}</b>}
          </button>
        ))}
      </nav>
      <button className="profile-link" onClick={() => setRoute("profile")}>
        <Avatar user={user} />
        <span><strong>{user.fullName || user.email}</strong><small>{user.role}</small></span>
      </button>
    </aside>
  );
}

function TopBar({ route, user, currentEmployee, setRoute }: { route: RouteKey; user: SessionUser; currentEmployee?: Employee | null; setRoute: (route: RouteKey) => void }) {
  const st = commandCenterModel("today").st;
  const isCommand = route === "command";
  const isSalesOverview = route === "salesOverview";
  return (
    <header className="hub-topbar">
      <div className="breadcrumbs">
        <button type="button" onClick={() => setRoute("command")}>{user.organizationName}</button>
        <i>/</i>
        {route === "employeeDetail" && <><button type="button" onClick={() => setRoute("employees")}>Сотрудники</button><i>/</i><strong>{currentEmployee?.fullName || currentEmployee?.email || routes[route]}</strong></>}
        {isSalesOverview && <><button type="button" onClick={() => setRoute("salesOverview")}>Продажи</button><i>/</i><strong>Обзор</strong></>}
        {route !== "employeeDetail" && !isSalesOverview && <strong>{routes[route]}</strong>}
      </div>
      <div className="topbar-actions">
        {isCommand && <span className="topbar-status" style={{ background: st.bg, borderColor: st.border, color: st.color }}><span style={{ background: st.dot }} />{st.label}</span>}
        <button className="icon-button" aria-label="Уведомления"><Icon name="bell" size={18} /><b className={isCommand ? "" : "is-dot"}>{isCommand ? "2" : ""}</b></button>
      </div>
    </header>
  );
}

export function Shell({ route, setRoute, selectedEmployeeId, openEmployeeRoute, user, data, reload, onUserUpdated, onLogout }: { route: RouteKey; setRoute: (route: RouteKey) => void; selectedEmployeeId: number | null; openEmployeeRoute: (employeeId: number) => void; user: SessionUser; data: AppData; reload: () => void; onUserUpdated: (user: SessionUser) => void; onLogout: () => void }) {
  const currentEmployee = route === "employeeDetail"
    ? data.employees.find((employee) => employee.id === selectedEmployeeId) ?? null
    : data.employees.find((employee) => employee.email === "a.kotova@edevs.tech") ?? data.employees[0] ?? null;
  function openEmployee(employee: Employee) {
    openEmployeeRoute(employee.id);
  }
  const isSalesWorkspace = route === "salesOverview";
  return (
    <div className="hub-shell">
      {isSalesWorkspace ? <SalesSidebar user={user} setRoute={setRoute} /> : <Sidebar route={route} user={user} setRoute={setRoute} />}
      <div className="hub-main">
        <TopBar route={route} user={user} currentEmployee={currentEmployee} setRoute={setRoute} />
        <main className="hub-scroll">
          <div className={`hub-page ${isSalesWorkspace ? "sales-workspace-page" : ""}`}>
            {route === "command" && <CommandCenter data={data} setRoute={setRoute} />}
            {route === "departments" && <DepartmentsPage data={data} setRoute={setRoute} />}
            {route === "employees" && <EmployeesPage employees={data.employees} reload={reload} openEmployee={openEmployee} />}
            {route === "employeeDetail" && currentEmployee && <EmployeeDetailPage employee={currentEmployee} reload={reload} setRoute={setRoute} />}
            {route === "employeeDetail" && !currentEmployee && <EmployeesPage employees={data.employees} reload={reload} openEmployee={openEmployee} />}
            {route === "products" && <ProductsPage products={data.products} reload={reload} />}
            {route === "profile" && <ProfilePage user={user} onUserUpdated={onUserUpdated} reload={reload} onLogout={onLogout} />}
            {route === "salesOverview" && <SalesOverviewPage products={data.products} />}
          </div>
        </main>
      </div>
    </div>
  );
}

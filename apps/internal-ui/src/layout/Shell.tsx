import type { AppData, Employee, RouteKey, SessionUser } from "../types";
import { Sidebar } from "./Sidebar";
import { SalesSidebar } from "./SalesSidebar";
import { ShellRouteContent } from "./ShellRouteContent";
import { TopBar } from "./TopBar";

export function Shell({ route, setRoute, selectedEmployeeId, openEmployeeRoute, user, data, reload, onUserUpdated, onLogout }: { route: RouteKey; setRoute: (route: RouteKey) => void; selectedEmployeeId: number | null; openEmployeeRoute: (employeeId: number) => void; user: SessionUser; data: AppData; reload: () => void; onUserUpdated: (user: SessionUser) => void; onLogout: () => void }) {
  const currentEmployee = route === "employeeDetail"
    ? data.employees.find((employee) => employee.id === selectedEmployeeId) ?? null
    : data.employees.find((employee) => employee.email === "a.kotova@edevs.tech") ?? data.employees[0] ?? null;
  function openEmployee(employee: Employee) {
    openEmployeeRoute(employee.id);
  }
  const isSalesWorkspace = route === "salesOverview" || route === "salesClientDetail" || route === "salesClients" || route === "salesDialogs";
  const isSalesDialogs = route === "salesDialogs";
  const isSalesClients = route === "salesClients";
  const isSalesClientDetail = route === "salesClientDetail";
  return (
    <div className="hub-shell">
      {isSalesWorkspace ? <SalesSidebar route={route} user={user} setRoute={setRoute} /> : <Sidebar route={route} user={user} setRoute={setRoute} />}
      <div className="hub-main">
        <TopBar route={route} user={user} currentEmployee={currentEmployee} setRoute={setRoute} />
        <main className={`hub-scroll ${isSalesDialogs ? "sales-dialogs-scroll" : ""}`}>
          <div className={`hub-page ${isSalesWorkspace ? "sales-workspace-page" : ""} ${isSalesDialogs ? "sales-dialogs-page" : ""} ${isSalesClients ? "sales-clients-page" : ""} ${isSalesClientDetail ? "sales-client-detail-page" : ""}`}>
            <ShellRouteContent route={route} data={data} currentEmployee={currentEmployee} openEmployee={openEmployee} reload={reload} setRoute={setRoute} user={user} onUserUpdated={onUserUpdated} onLogout={onLogout} />
          </div>
        </main>
      </div>
    </div>
  );
}

import type { AppData, Employee, Product, RouteKey, SessionUser } from "../types";
import { Sidebar } from "./Sidebar";
import { SalesSidebar } from "./SalesSidebar";
import { ShellRouteContent } from "./ShellRouteContent";
import { TopBar } from "./TopBar";

export function Shell({ route, setRoute, selectedEmployeeId, selectedProductId, openEmployeeRoute, openProductRoute, user, data, reload, onUserUpdated, onLogout }: { route: RouteKey; setRoute: (route: RouteKey) => void; selectedEmployeeId: number | null; selectedProductId: number | null; openEmployeeRoute: (employeeId: number) => void; openProductRoute: (productId: number) => void; user: SessionUser; data: AppData; reload: () => void; onUserUpdated: (user: SessionUser) => void; onLogout: () => void }) {
  const currentEmployee = route === "employeeDetail"
    ? data.employees.find((employee) => employee.id === selectedEmployeeId) ?? null
    : data.employees.find((employee) => employee.email === "a.kotova@edevs.tech") ?? data.employees[0] ?? null;
  function openEmployee(employee: Employee) {
    openEmployeeRoute(employee.id);
  }
  const currentProduct = route === "productDetail" ? data.products.find((product) => product.id === selectedProductId) ?? null : null;
  function openProduct(product: Product) {
    openProductRoute(product.id);
  }
  const isSalesWorkspace = route === "salesOverview" || route === "salesClientDetail" || route === "salesClients" || route === "salesDialogs" || route === "salesOrderDetail" || route === "salesOrders";
  const isSalesDialogs = route === "salesDialogs";
  const isSalesClients = route === "salesClients";
  const isSalesClientDetail = route === "salesClientDetail";
  const isSalesOrderDetail = route === "salesOrderDetail";
  const isSalesOrders = route === "salesOrderDetail" || route === "salesOrders";
  // OPERATOR работает только в пространстве продаж, поэтому всегда видит sales-sidebar (SPEC-HUB-0004 §9).
  const showSalesSidebar = isSalesWorkspace || user.role === "OPERATOR";
  return (
    <div className="hub-shell">
      {showSalesSidebar ? <SalesSidebar route={route} user={user} setRoute={setRoute} /> : <Sidebar route={route} user={user} setRoute={setRoute} />}
      <div className="hub-main">
        <TopBar route={route} user={user} currentEmployee={currentEmployee} currentProduct={currentProduct} setRoute={setRoute} />
        <main className={`hub-scroll ${isSalesDialogs ? "sales-dialogs-scroll" : ""}`}>
          <div className={`hub-page ${isSalesWorkspace ? "sales-workspace-page" : ""} ${isSalesDialogs ? "sales-dialogs-page" : ""} ${isSalesClients ? "sales-clients-page" : ""} ${isSalesClientDetail ? "sales-client-detail-page" : ""} ${isSalesOrderDetail ? "sales-order-detail-page" : ""} ${isSalesOrders ? "sales-orders-page" : ""}`}>
            <ShellRouteContent route={route} data={data} currentEmployee={currentEmployee} currentProduct={currentProduct} openEmployee={openEmployee} openProduct={openProduct} reload={reload} setRoute={setRoute} user={user} onUserUpdated={onUserUpdated} onLogout={onLogout} />
          </div>
        </main>
      </div>
    </div>
  );
}

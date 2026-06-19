import { CommandCenter } from "../features/command/CommandCenter";
import { DepartmentsPage } from "../features/departments/DepartmentsPage";
import { EmployeeDetailPage, EmployeesPage } from "../features/employees/EmployeesPage";
import { ProductsPage } from "../features/products/ProductsPage";
import { ProductDetailPage } from "../features/products/detail/ProductDetailPage";
import { ProfilePage } from "../features/profile/ProfilePage";
import { SalesClientDetailPage } from "../features/sales/client-detail/SalesClientDetailPage";
import { SalesOrderDetailPage } from "../features/sales/order-detail/SalesOrderDetailPage";
import { SalesClientsPage } from "../features/sales/SalesClientsPage";
import { SalesDialogsPage } from "../features/sales/SalesDialogsPage";
import { SalesOrdersPage } from "../features/sales/orders/SalesOrdersPage";
import { SalesOverviewPage } from "../features/sales/SalesOverviewPage";
import type { AppData, Employee, Product, RouteKey, SessionUser } from "../types";

export function ShellRouteContent({ route, data, currentEmployee, currentProduct, openEmployee, openProduct, reload, setRoute, user, onUserUpdated, onLogout }: { route: RouteKey; data: AppData; currentEmployee: Employee | null; currentProduct: Product | null; openEmployee: (employee: Employee) => void; openProduct: (product: Product) => void; reload: () => void; setRoute: (route: RouteKey) => void; user: SessionUser; onUserUpdated: (user: SessionUser) => void; onLogout: () => void }) {
  return (
    <>
      {route === "command" && <CommandCenter data={data} setRoute={setRoute} />}
      {route === "departments" && <DepartmentsPage data={data} setRoute={setRoute} />}
      {route === "employees" && <EmployeesPage employees={data.employees} reload={reload} openEmployee={openEmployee} />}
      {route === "employeeDetail" && currentEmployee && <EmployeeDetailPage employee={currentEmployee} reload={reload} setRoute={setRoute} />}
      {route === "employeeDetail" && !currentEmployee && <EmployeesPage employees={data.employees} reload={reload} openEmployee={openEmployee} />}
      {route === "products" && <ProductsPage departments={data.departments} products={data.products} reload={reload} openProduct={openProduct} />}
      {route === "productDetail" && currentProduct && <ProductDetailPage product={currentProduct} departments={data.departments} reload={reload} />}
      {route === "productDetail" && !currentProduct && <ProductsPage departments={data.departments} products={data.products} reload={reload} openProduct={openProduct} />}
      {route === "profile" && <ProfilePage user={user} onUserUpdated={onUserUpdated} reload={reload} onLogout={onLogout} />}
      {route === "salesClients" && <SalesClientsPage openClient={() => setRoute("salesClientDetail")} />}
      {route === "salesClientDetail" && <SalesClientDetailPage setRoute={setRoute} />}
      {route === "salesOverview" && <SalesOverviewPage products={data.products} />}
      {route === "salesDialogs" && <SalesDialogsPage />}
      {route === "salesOrderDetail" && <SalesOrderDetailPage setRoute={setRoute} />}
      {route === "salesOrders" && <SalesOrdersPage setRoute={setRoute} />}
    </>
  );
}

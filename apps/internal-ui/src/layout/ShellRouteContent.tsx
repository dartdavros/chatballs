import { AiAgentsPage } from "../features/ai/AiAgentsPage";
import { AiAgentCreatePage } from "../features/ai/create/AiAgentCreatePage";
import { AiAgentDetailPage } from "../features/ai/detail/AiAgentDetailPage";
import { KnowledgeDetailPage } from "../features/ai/knowledge/KnowledgeDetailPage";
import { KnowledgePage } from "../features/ai/knowledge/KnowledgePage";
import { CommandCenter } from "../features/command/CommandCenter";
import { IntegrationsPage } from "../features/integrations/IntegrationsPage";
import { DepartmentsPage } from "../features/departments/DepartmentsPage";
import { EmployeeDetailPage, EmployeesPage } from "../features/employees/EmployeesPage";
import { ProductsPage } from "../features/products/ProductsPage";
import { ProductDetailPage } from "../features/products/detail/ProductDetailPage";
import { ProfilePage } from "../features/profile/ProfilePage";
import { SalesClientDetailPage } from "../features/sales/client-detail/SalesClientDetailPage";
import { SalesClientsPage } from "../features/sales/SalesClientsPage";
import { SalesDialogsPage } from "../features/sales/SalesDialogsPage";
import { SalesRegistryPage } from "../features/sales/registry/SalesRegistryPage";
import { SaleDetailPage } from "../features/sales/sale-detail/SaleDetailPage";
import { SalesOverviewPage } from "../features/sales/SalesOverviewPage";
import { SupportDialogsPage } from "../features/support/SupportDialogsPage";
import { SupportOverviewPage } from "../features/support/SupportOverviewPage";
import type { AppData, Employee, Product, RouteKey, SessionUser } from "../types";

export function ShellRouteContent({ route, data, currentEmployee, currentProduct, selectedProductCode, selectedAgentId, selectedKnowledgeId, selectedConversationId, selectedClientId, openClient, selectedOrderId, openOrder, openConversation, openEmployee, openProduct, openAgentCreate, openAgent, openKnowledge, onAgentLoaded, reload, setRoute, user, onUserUpdated, onLogout }: { route: RouteKey; data: AppData; currentEmployee: Employee | null; currentProduct: Product | null; selectedProductCode: string | null; selectedAgentId: number | null; selectedKnowledgeId: number | null; selectedConversationId: number | null; selectedClientId: number | null; openClient: (clientId: number) => void; selectedOrderId: number | null; openOrder: (orderId: number) => void; openConversation: (conversationId: number) => void; openEmployee: (employee: Employee) => void; openProduct: (product: Product) => void; openAgentCreate: (productCode: string | null) => void; openAgent: (agentId: number) => void; openKnowledge: (knowledgeId: number) => void; onAgentLoaded: (name: string | null) => void; reload: () => void; setRoute: (route: RouteKey) => void; user: SessionUser; onUserUpdated: (user: SessionUser) => void; onLogout: () => void }) {
  return (
    <>
      {route === "command" && <CommandCenter data={data} setRoute={setRoute} />}
      {route === "departments" && <DepartmentsPage data={data} setRoute={setRoute} />}
      {route === "employees" && <EmployeesPage employees={data.employees} reload={reload} openEmployee={openEmployee} />}
      {route === "employeeDetail" && currentEmployee && <EmployeeDetailPage employee={currentEmployee} reload={reload} setRoute={setRoute} />}
      {route === "employeeDetail" && !currentEmployee && <EmployeesPage employees={data.employees} reload={reload} openEmployee={openEmployee} />}
      {route === "products" && <ProductsPage departments={data.departments} products={data.products} reload={reload} openProduct={openProduct} />}
      {route === "productDetail" && currentProduct && <ProductDetailPage product={currentProduct} departments={data.departments} reload={reload} openAgentCreate={openAgentCreate} openAgent={openAgent} />}
      {route === "productDetail" && !currentProduct && <ProductsPage departments={data.departments} products={data.products} reload={reload} openProduct={openProduct} />}
      {route === "profile" && <ProfilePage user={user} onUserUpdated={onUserUpdated} reload={reload} onLogout={onLogout} />}
      {route === "salesClients" && <SalesClientsPage openClient={openClient} />}
      {route === "salesClientDetail" && <SalesClientDetailPage contactId={selectedClientId} setRoute={setRoute} />}
      {route === "salesOverview" && <SalesOverviewPage />}
      {route === "supportOverview" && <SupportOverviewPage />}
      {route === "supportDialogs" && <SupportDialogsPage initialConversationId={selectedConversationId} />}
      {route === "salesDialogs" && <SalesDialogsPage initialConversationId={selectedConversationId} />}
      {route === "salesOrderDetail" && <SaleDetailPage saleId={selectedOrderId} role={user.role} setRoute={setRoute} openDialog={openConversation} />}
      {route === "salesOrders" && <SalesRegistryPage products={data.products} setRoute={setRoute} openSale={openOrder} openDialog={openConversation} />}
      {route === "aiAgents" && <AiAgentsPage agents={data.agents} reload={reload} openAgentCreate={openAgentCreate} openAgent={openAgent} />}
      {route === "aiAgentCreate" && <AiAgentCreatePage selectedProductCode={selectedProductCode} reload={reload} setRoute={setRoute} openAgent={openAgent} />}
      {route === "aiAgentDetail" && <AiAgentDetailPage agentId={selectedAgentId} openKnowledge={openKnowledge} onAgentLoaded={onAgentLoaded} />}
      {route === "aiKnowledge" && <KnowledgePage openKnowledge={openKnowledge} />}
      {route === "aiKnowledgeDetail" && <KnowledgeDetailPage knowledgeId={selectedKnowledgeId} setRoute={setRoute} onLoaded={onAgentLoaded} />}
      {route === "integrations" && <IntegrationsPage />}
    </>
  );
}

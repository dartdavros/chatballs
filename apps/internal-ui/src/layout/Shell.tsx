import { notification as antToast } from "antd";
import { useCallback, useEffect, useRef, useState } from "react";

import type { AppData, Employee, Product, RouteKey, SessionUser } from "../types";
import { AiSubnav } from "../features/ai/AiSubnav";
import { NotificationDrawer } from "../features/notifications/NotificationDrawer";
import { fetchNotifications, markAllRead, markRead, type AppNotification } from "../features/notifications/model";
import { fetchWaitingCount } from "../features/conversations/model";
import { Sidebar } from "./Sidebar";
import { SalesSidebar } from "./SalesSidebar";
import { SupportSidebar } from "./SupportSidebar";
import { ShellRouteContent } from "./ShellRouteContent";
import { TopBar } from "./TopBar";

export function Shell({ route, setRoute, selectedEmployeeId, selectedProductId, selectedProductCode, selectedAgentId, selectedKnowledgeId, selectedConversationId, selectedClientId, selectedOrderId, openEmployeeRoute, openProductRoute, openAgentCreateRoute, openAgentRoute, openKnowledgeRoute, openConversationRoute, openClientRoute, openOrderRoute, user, data, reload, onUserUpdated, onLogout }: { route: RouteKey; setRoute: (route: RouteKey) => void; selectedEmployeeId: number | null; selectedProductId: number | null; selectedProductCode: string | null; selectedAgentId: number | null; selectedKnowledgeId: number | null; selectedConversationId: number | null; selectedClientId: number | null; selectedOrderId: number | null; openEmployeeRoute: (employeeId: number) => void; openProductRoute: (productId: number) => void; openAgentCreateRoute: (productCode: string | null) => void; openAgentRoute: (agentId: number) => void; openKnowledgeRoute: (knowledgeId: number) => void; openConversationRoute: (conversationId: number) => void; openClientRoute: (clientId: number) => void; openOrderRoute: (orderId: number) => void; user: SessionUser; data: AppData; reload: () => void; onUserUpdated: (user: SessionUser) => void; onLogout: () => void }) {
  const [agentName, setAgentName] = useState<string | null>(null);
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifOpen, setNotifOpen] = useState(false);
  const [waitingCount, setWaitingCount] = useState(0);
  const prevUnread = useRef<number | null>(null);

  const loadWaitingCount = useCallback(async () => {
    try {
      setWaitingCount(await fetchWaitingCount());
    } catch {
      /* ignore */
    }
  }, []);

  const loadNotifications = useCallback(async () => {
    try {
      const payload = await fetchNotifications();
      setNotifications(payload.items);
      setUnreadCount(payload.unreadCount);
      // Тост при появлении новых непрочитанных (после первой загрузки).
      if (prevUnread.current !== null && payload.unreadCount > prevUnread.current) {
        const latest = payload.items.find((item) => item.unread);
        if (latest) antToast.open({ message: latest.title, description: latest.body, placement: "bottomRight" });
      }
      prevUnread.current = payload.unreadCount;
    } catch {
      /* ignore transient errors */
    }
  }, []);

  useEffect(() => {
    const tick = () => {
      void loadNotifications();
      void loadWaitingCount();
    };
    tick();
    const timer = setInterval(tick, 15000);
    return () => clearInterval(timer);
  }, [loadNotifications, loadWaitingCount]);

  async function onNotificationClick(notification: AppNotification) {
    setNotifOpen(false);
    if (notification.unread) {
      await markRead([notification.id]).catch(() => undefined);
      void loadNotifications();
    }
    if (notification.targetRoute === "salesDialogs" && notification.targetId) {
      openConversationRoute(Number(notification.targetId));
    } else if (notification.targetRoute) {
      setRoute(notification.targetRoute as RouteKey);
    }
  }

  async function onMarkAll() {
    await markAllRead().catch(() => undefined);
    void loadNotifications();
  }

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
  const isSupportWorkspace = route === "supportOverview" || route === "supportDialogs";
  const isSalesDialogs = route === "salesDialogs";
  const isSupportDialogs = route === "supportDialogs";
  const isDialogsWorkspace = isSalesDialogs || isSupportDialogs;
  const isSalesClients = route === "salesClients";
  const isSalesClientDetail = route === "salesClientDetail";
  const isSalesOrderDetail = route === "salesOrderDetail";
  const isSalesOrders = route === "salesOrderDetail" || route === "salesOrders";
  // Подменю AI показываем только там, где оно есть в baseline.
  const isAiSection = route === "aiAgents" || route === "aiKnowledge" || route === "aiUsage";
  const isAiFullWidth = route === "aiAgentCreate";
  // Сотрудник (EMPLOYEE) работает в пространстве своего отдела (SPEC-HUB-0004 §9 +
  // §0010 §10): sales → sales-sidebar, support → support-sidebar. Compat-адаптер
  // этапа 1 (ADR-HUB-0027): department по-прежнему определяет рабочее пространство.
  const showSalesSidebar = isSalesWorkspace || (user.role === "EMPLOYEE" && user.department !== "support" && !isSupportWorkspace);
  const showSupportSidebar = isSupportWorkspace || (user.role === "EMPLOYEE" && user.department === "support");
  return (
    <div className="hub-shell">
      {showSupportSidebar ? <SupportSidebar route={route} user={user} setRoute={setRoute} waitingCount={waitingCount} /> : showSalesSidebar ? <SalesSidebar route={route} user={user} setRoute={setRoute} waitingCount={waitingCount} /> : <Sidebar route={route} user={user} setRoute={setRoute} />}
      <div className="hub-main">
        <TopBar route={route} user={user} currentEmployee={currentEmployee} currentProduct={currentProduct} currentAgentName={agentName} setRoute={setRoute} unreadCount={unreadCount} onOpenNotifications={() => { setNotifOpen(true); void loadNotifications(); }} />
        {isAiSection && <AiSubnav route={route} setRoute={setRoute} />}
        <main className={`hub-scroll ${isDialogsWorkspace ? "sales-dialogs-scroll" : ""} ${isAiFullWidth ? "ai-fullwidth-scroll" : ""}`}>
          <div className={`hub-page ${isSalesWorkspace || isSupportWorkspace ? "sales-workspace-page" : ""} ${isDialogsWorkspace ? "sales-dialogs-page" : ""} ${isSalesClients ? "sales-clients-page" : ""} ${isSalesClientDetail ? "sales-client-detail-page" : ""} ${isSalesOrderDetail ? "sales-order-detail-page" : ""} ${isSalesOrders ? "sales-orders-page" : ""} ${isAiFullWidth ? "ai-fullwidth-page" : ""}`}>
            <ShellRouteContent route={route} data={data} currentEmployee={currentEmployee} currentProduct={currentProduct} selectedProductCode={selectedProductCode} selectedAgentId={selectedAgentId} selectedKnowledgeId={selectedKnowledgeId} selectedConversationId={selectedConversationId} selectedClientId={selectedClientId} openClient={openClientRoute} selectedOrderId={selectedOrderId} openOrder={openOrderRoute} openConversation={openConversationRoute} openEmployee={openEmployee} openProduct={openProduct} openAgentCreate={openAgentCreateRoute} openAgent={openAgentRoute} openKnowledge={openKnowledgeRoute} onAgentLoaded={setAgentName} reload={reload} setRoute={setRoute} user={user} onUserUpdated={onUserUpdated} onLogout={onLogout} />
          </div>
        </main>
      </div>
      <NotificationDrawer
        open={notifOpen}
        items={notifications}
        unreadCount={unreadCount}
        onClose={() => setNotifOpen(false)}
        onItemClick={onNotificationClick}
        onMarkAll={onMarkAll}
      />
    </div>
  );
}

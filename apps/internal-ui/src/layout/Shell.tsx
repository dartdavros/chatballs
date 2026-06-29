import { notification as antToast } from "antd";
import { useCallback, useEffect, useRef, useState } from "react";

import type { AppData, Employee, Product, RouteKey, SessionUser } from "../types";
import { AiSubnav } from "../features/ai/AiSubnav";
import { NotificationDrawer } from "../features/notifications/NotificationDrawer";
import { fetchNotifications, markAllRead, markRead, type AppNotification } from "../features/notifications/model";
import { fetchWaitingCount } from "../features/sales/dialogs/model";
import { Sidebar } from "./Sidebar";
import { SalesSidebar } from "./SalesSidebar";
import { ShellRouteContent } from "./ShellRouteContent";
import { TopBar } from "./TopBar";

export function Shell({ route, setRoute, selectedEmployeeId, selectedProductId, selectedProductCode, selectedAgentId, selectedReleaseId, selectedConversationId, selectedClientId, openEmployeeRoute, openProductRoute, openAgentCreateRoute, openAgentRoute, openReleaseRoute, openConversationRoute, openClientRoute, user, data, reload, onUserUpdated, onLogout }: { route: RouteKey; setRoute: (route: RouteKey) => void; selectedEmployeeId: number | null; selectedProductId: number | null; selectedProductCode: string | null; selectedAgentId: number | null; selectedReleaseId: number | null; selectedConversationId: number | null; selectedClientId: number | null; openEmployeeRoute: (employeeId: number) => void; openProductRoute: (productId: number) => void; openAgentCreateRoute: (productCode: string | null) => void; openAgentRoute: (agentId: number) => void; openReleaseRoute: (releaseId: number) => void; openConversationRoute: (conversationId: number) => void; openClientRoute: (clientId: number) => void; user: SessionUser; data: AppData; reload: () => void; onUserUpdated: (user: SessionUser) => void; onLogout: () => void }) {
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
  const isSalesDialogs = route === "salesDialogs";
  const isSalesClients = route === "salesClients";
  const isSalesClientDetail = route === "salesClientDetail";
  const isSalesOrderDetail = route === "salesOrderDetail";
  const isSalesOrders = route === "salesOrderDetail" || route === "salesOrders";
  // Подменю AI показываем только там, где оно есть в baseline.
  const isAiSection = route === "aiAgents" || route === "aiUsage";
  const isAiFullWidth = route === "aiAgentCreate" || route === "aiRelease" || route === "aiTestChat";
  // OPERATOR работает только в пространстве продаж, поэтому всегда видит sales-sidebar (SPEC-HUB-0004 §9).
  const showSalesSidebar = isSalesWorkspace || user.role === "OPERATOR";
  return (
    <div className="hub-shell">
      {showSalesSidebar ? <SalesSidebar route={route} user={user} setRoute={setRoute} waitingCount={waitingCount} /> : <Sidebar route={route} user={user} setRoute={setRoute} />}
      <div className="hub-main">
        <TopBar route={route} user={user} currentEmployee={currentEmployee} currentProduct={currentProduct} currentAgentName={agentName} setRoute={setRoute} unreadCount={unreadCount} onOpenNotifications={() => { setNotifOpen(true); void loadNotifications(); }} />
        {isAiSection && <AiSubnav route={route} setRoute={setRoute} />}
        <main className={`hub-scroll ${isSalesDialogs ? "sales-dialogs-scroll" : ""} ${isAiFullWidth ? "ai-fullwidth-scroll" : ""}`}>
          <div className={`hub-page ${isSalesWorkspace ? "sales-workspace-page" : ""} ${isSalesDialogs ? "sales-dialogs-page" : ""} ${isSalesClients ? "sales-clients-page" : ""} ${isSalesClientDetail ? "sales-client-detail-page" : ""} ${isSalesOrderDetail ? "sales-order-detail-page" : ""} ${isSalesOrders ? "sales-orders-page" : ""} ${isAiFullWidth ? "ai-fullwidth-page" : ""}`}>
            <ShellRouteContent route={route} data={data} currentEmployee={currentEmployee} currentProduct={currentProduct} selectedProductCode={selectedProductCode} selectedAgentId={selectedAgentId} selectedReleaseId={selectedReleaseId} selectedConversationId={selectedConversationId} selectedClientId={selectedClientId} openClient={openClientRoute} openEmployee={openEmployee} openProduct={openProduct} openAgentCreate={openAgentCreateRoute} openAgent={openAgentRoute} openRelease={openReleaseRoute} onAgentLoaded={setAgentName} reload={reload} setRoute={setRoute} user={user} onUserUpdated={onUserUpdated} onLogout={onLogout} />
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

import { notification as antToast } from "antd";
import { useCallback, useEffect, useRef, useState } from "react";

import type { AppData, Employee, RouteKey, SessionUser } from "../types";
import { NotificationDrawer } from "../features/notifications/NotificationDrawer";
import { fetchNotifications, markAllRead, markRead, type AppNotification } from "../features/notifications/model";
import { fetchWaitingCount } from "../features/conversations/model";
import { useChatScope } from "../features/chat/useChatScope";
import { isManager } from "../auth/access";
import { Sidebar } from "./Sidebar";
import { ShellRouteContent } from "./ShellRouteContent";
import { TopBar } from "./TopBar";

export function Shell({ route, setRoute, selectedEmployeeId, selectedProductCode, selectedAgentId, selectedKnowledgeId, selectedConversationId, selectedClientId, selectedChannelId, selectedSupportPortalId, openChannelRoute, openSupportPortalRoute, openEmployeeRoute, openAgentCreateRoute, openAgentRoute, openKnowledgeRoute, openConversationRoute, openClientRoute, user, data, reload, onUserUpdated, onLogout }: { route: RouteKey; setRoute: (route: RouteKey) => void; selectedEmployeeId: number | null; selectedProductCode: string | null; selectedAgentId: number | null; selectedKnowledgeId: number | null; selectedConversationId: number | null; selectedClientId: number | null; selectedChannelId: number | null; selectedSupportPortalId: number | null; openEmployeeRoute: (employeeId: number) => void; openAgentCreateRoute: (productCode: string | null) => void; openAgentRoute: (agentId: number) => void; openKnowledgeRoute: (knowledgeId: number) => void; openConversationRoute: (conversationId: number) => void; openClientRoute: (clientId: number) => void; openChannelRoute: (channelId: number) => void; openSupportPortalRoute: (portalId: number) => void; user: SessionUser; data: AppData; reload: () => void; onUserUpdated: (user: SessionUser) => void; onLogout: () => void }) {
  const [agentName, setAgentName] = useState<string | null>(null);
  const [channelName, setChannelName] = useState<string | null>(null);
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifOpen, setNotifOpen] = useState(false);
  const [waitingCount, setWaitingCount] = useState(0);
  const prevUnread = useRef<number | null>(null);
  const manager = isManager(user);
  // Охват чата живёт здесь: сотрудницкий сайдбар и страница чата делят одно
  // состояние (дизайн-базлайн v2 §4.1).
  const chatScope = useChatScope(true);

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
    // «salesDialogs»/«conversations» — легаси-маршруты старых уведомлений в БД.
    const targetRoute = notification.targetRoute === "salesDialogs" || notification.targetRoute === "conversations"
      ? "chat"
      : notification.targetRoute;
    if (targetRoute === "chat" && notification.targetId) {
      openConversationRoute(Number(notification.targetId));
    } else if (targetRoute) {
      setRoute(targetRoute as RouteKey);
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
  const isSalesWorkspace = route === "salesClientDetail" || route === "salesClients" || route === "chat";
  const isSupportWorkspace = route === "supportPortals" || route === "supportPortalDetail";
  const isDialogsWorkspace = route === "chat";
  const isSalesClients = route === "salesClients";
  const isSalesClientDetail = route === "salesClientDetail";
  const isAiFullWidth = false;
  const isKnowledgeLibrary = route === "aiKnowledge";
  const isKnowledgeEditor = route === "aiKnowledgeCreate" || route === "aiKnowledgeDetail";
  return (
    <div className={`hub-shell ${isDialogsWorkspace ? "is-chat-route" : ""}`}>
      <Sidebar route={route} user={user} setRoute={setRoute} onLogout={onLogout} waitingCount={waitingCount} chatScope={chatScope.scope} setChatScope={chatScope.setScope} chatCounters={chatScope.counters} unreadCount={unreadCount} onOpenNotifications={() => { setNotifOpen(true); void loadNotifications(); }} />
      <div className="hub-main">
        {/* У сотрудника верхней панели нет (дизайн-базлайн v2 §4.1). */}
        {/* Дизайн-базлайн v2 (A1/A2): верхней панели в чате нет и у менеджера;
            уведомления открываются из меню профиля в сайдбаре. */}
        {manager && !isDialogsWorkspace && <TopBar route={route} user={user} currentEmployee={currentEmployee} currentAgentName={agentName} currentChannelName={channelName} setRoute={setRoute} unreadCount={unreadCount} onOpenNotifications={() => { setNotifOpen(true); void loadNotifications(); }} />}
        <main className={`hub-scroll ${isDialogsWorkspace ? "sales-dialogs-scroll" : ""} ${isAiFullWidth ? "ai-fullwidth-scroll" : ""}`}>
          <div className={`hub-page ${isSalesWorkspace || isSupportWorkspace ? "sales-workspace-page" : ""} ${isDialogsWorkspace ? "sales-dialogs-page" : ""} ${isSalesClients ? "sales-clients-page" : ""} ${isSalesClientDetail ? "sales-client-detail-page" : ""} ${isAiFullWidth ? "ai-fullwidth-page" : ""} ${isKnowledgeLibrary ? "ai-knowledge-library-page" : ""} ${isKnowledgeEditor ? "ai-knowledge-editor-page" : ""}`}>
            <ShellRouteContent chatScope={chatScope.scope} setChatScope={chatScope.setScope} chatCounters={chatScope.counters} chatScopeSwitcher={manager} route={route} data={data} currentEmployee={currentEmployee} selectedProductCode={selectedProductCode} selectedAgentId={selectedAgentId} selectedKnowledgeId={selectedKnowledgeId} selectedConversationId={selectedConversationId} selectedClientId={selectedClientId} openClient={openClientRoute} selectedChannelId={selectedChannelId} openChannel={openChannelRoute} selectedSupportPortalId={selectedSupportPortalId} openSupportPortal={openSupportPortalRoute} openConversation={openConversationRoute} openEmployee={openEmployee} openAgentCreate={openAgentCreateRoute} openAgent={openAgentRoute} openKnowledge={openKnowledgeRoute} onAgentLoaded={setAgentName} onChannelLoaded={setChannelName} reload={reload} setRoute={setRoute} user={user} onUserUpdated={onUserUpdated} onLogout={onLogout} />
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

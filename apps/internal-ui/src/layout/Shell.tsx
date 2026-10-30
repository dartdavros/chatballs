import { useCallback, useEffect, useState } from "react";

import type { AppData, AuthenticatedUser, Employee, RouteKey, SessionUser } from "../types";
import type { SettingsSectionKey } from "../features/settings/sections";
import type { PortalSettingsSectionKey } from "../features/support-portals/sections";
import { NotificationDrawer } from "../features/notifications/NotificationDrawer";
import { fetchNotifications, markAllRead, markRead, type AppNotification } from "../features/notifications/model";
import { useNotificationAlerts } from "../features/notifications/useNotificationAlerts";
import { fetchWaitingCount } from "../features/conversations/model";
import { useRealtime, useRealtimeEvent } from "../features/realtime/RealtimeProvider";
import { useChatScope } from "../features/chat/useChatScope";
import { isManager } from "../auth/access";
import { DemoInstallBanner } from "../features/settings/DemoInstallBanner";
import { Sidebar } from "./Sidebar";
import { OnboardingLauncher } from "../features/onboarding/OnboardingLauncher";
import { OnboardingOverlay } from "../features/onboarding/OnboardingOverlay";
import { OnboardingTour } from "../features/onboarding/OnboardingTour";
import { OnboardingProvider, useOnboardingState } from "../features/onboarding/useOnboarding";
import { UpdateBanner } from "../features/updates/UpdateBanner";
import { ShellRouteContent } from "./ShellRouteContent";

export function Shell({ route, setRoute, settingsSection, openSettingsRoute, selectedEmployeeId, selectedAgentId, selectedKnowledgeId, selectedConversationId, selectedClientId, selectedChannelId, selectedIntegrationId, openWebIntegrationRoute, openServiceConnectionRoute, selectedSupportPortalId, portalSettingsSection, openChannelRoute, openSupportPortalRoute, openPortalSettingsRoute, openEmployeeRoute, openAgentRoute, openKnowledgeRoute, openKnowledgeEditorRoute, openConversationRoute, openClientRoute, user, data, reload, onUserUpdated, onLogout, onSwitchOrganization, onOrganizationCreated }: { route: RouteKey; setRoute: (route: RouteKey) => void; settingsSection: SettingsSectionKey | null; openSettingsRoute: (section: SettingsSectionKey | null) => void; selectedEmployeeId: number | null; selectedAgentId: number | null; selectedKnowledgeId: number | null; selectedConversationId: number | null; selectedClientId: number | null; selectedChannelId: number | null; selectedIntegrationId: number | null; openWebIntegrationRoute: (id: number) => void; openServiceConnectionRoute: (id: number) => void; selectedSupportPortalId: number | null; portalSettingsSection: PortalSettingsSectionKey | null; openEmployeeRoute: (employeeId: number) => void; openAgentRoute: (agentId: number) => void; openKnowledgeRoute: (knowledgeId: number) => void;
  openKnowledgeEditorRoute: (knowledgeId: number | null) => void; openConversationRoute: (conversationId: number) => void; openClientRoute: (clientId: number) => void; openChannelRoute: (channelId: number) => void; openSupportPortalRoute: (portalId: number) => void; openPortalSettingsRoute: (portalId: number, section?: PortalSettingsSectionKey) => void; user: SessionUser; data: AppData; reload: () => void; onUserUpdated: (user: SessionUser) => void; onLogout: () => void; onSwitchOrganization: (organizationPublicId: string) => void; onOrganizationCreated: (identity: AuthenticatedUser, organizationPublicId: string) => void }) {
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifOpen, setNotifOpen] = useState(false);
  const [waitingCount, setWaitingCount] = useState(0);
  // Кадры S2/M1: рейка или ☰ раскрывают сайдбар поверх контента.
  const [sidebarExpanded, setSidebarExpanded] = useState(false);
  const manager = isManager(user);
  // Охват чата живёт здесь: сотрудницкий сайдбар и страница чата делят одно
  // состояние (дизайн-базлайн v2 §4.1).
  const chatScope = useChatScope(true);
  // Онбординг «Начало работы»: окно, тур и пилюля возврата. Состояние живёт
  // здесь, потому что ссылка «Начало работы» в субменю «Настроек» читает тот
  // же прогресс.
  const onboarding = useOnboardingState({ user, setRoute, openSettings: openSettingsRoute });

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
      setNotifications(payload.items ?? []);
      setUnreadCount(payload.unreadCount ?? 0);
    } catch {
      /* ignore transient errors */
    }
  }, []);

  // Уведомление доезжает событием, а не следующим опросом: раньше оператор
  // узнавал о ждущем диалоге в среднем через восемь секунд после того, как
  // клиент написал, и только если вкладка была открыта на чате.
  const realtime = useRealtime();
  useRealtimeEvent("notifications.changed", () => void loadNotifications());
  useRealtimeEvent("inbox.changed", () => void loadWaitingCount());

  useEffect(() => {
    void loadNotifications();
    void loadWaitingCount();
  }, [loadNotifications, loadWaitingCount]);

  useEffect(() => {
    // Опрос остаётся страховкой на случай обрыва сокета и потому разрежается,
    // пока тот жив. Смена состояния соединения меняет только интервал: если
    // перезапускать вместе с ним и загрузку, недоступный сокет с его
    // переподключениями превращается в поток лишних запросов.
    const tick = () => {
      void loadNotifications();
      void loadWaitingCount();
    };
    const timer = setInterval(tick, realtime.connected ? 60000 : 15000);
    return () => clearInterval(timer);
  }, [loadNotifications, loadWaitingCount, realtime.connected]);

  // Тост и системное уведомление — по идентификаторам пришедшего, а не по
  // росту счётчика непрочитанных.
  const notificationAlerts = useNotificationAlerts({ items: notifications, onOpen: (item) => void onNotificationClick(item) });

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

  function openEmployee(employee: Employee) {
    openEmployeeRoute(employee.id);
  }
  const isSalesWorkspace = route === "chat";
  const isSupportWorkspace = route === "supportPortals" || route === "supportPortalDetail" || route === "supportPortalSettings";
  const isDialogsWorkspace = route === "chat";
  const isAiFullWidth = false;
  // «База знаний» — своя лента на --surface-feed и полноэкранный редактор
  // (дизайн-базлайн v2, кадры KB1–KB9).
  const isKnowledge = route === "knowledge" || route === "knowledgeDetail"
    || route === "knowledgeCategories" || route === "knowledgeImport";
  const isKnowledgeEditor = route === "knowledgeCreate" || route === "knowledgeEdit";
  // «Настройки» занимают всю область как чат: своё субменю 240px и своя лента.
  const isSettings = route === "ruleJournal" || route === "settings" || route === "webIntegrationSettings" || route === "mcpServerCreate" || route === "httpServerCreate" || route === "integrationServers" || route === "serviceIntegrations" || route === "serviceConnection";
  // «Профиль» — своя лента на --surface-feed и мобильные подэкраны (кадр M).
  // Библиотека шаблонов сотрудника открывается из того же меню и живёт на
  // такой же ленте.
  const isProfile = route === "profile" || route === "replyTemplates";
  // «Контакты» — своя лента на --surface-feed (кадры K1–K5).
  const isContacts = route === "salesClients" || route === "salesClientDetail";
  // «Агенты» — своя лента на --surface-feed (кадры G1–G5, S1).
  const isAgents = route === "agents" || route === "agentDetail" || route === "skills";
  // «Сотрудники» — своя лента на --surface-feed (кадры E1–E4).
  const isEmployees = route === "employees" || route === "employeeDetail";
  // «Аудит действий» — отдельный экран из субменю «Настроек», в общем ритме
  // списков: своя лента на --surface-feed и колонка 1220px по центру.
  const isAudit = route === "administrationAudit";
  // «Порталы» — своя лента на --surface-feed и полноэкранные сплиты (кадры PT1–PT8).
  const isPortals = route === "supportPortals" || route === "supportPortalDetail" || route === "supportPortalSettings";
  return (
    <OnboardingProvider value={onboarding}>
      <div className={`hub-shell ${isDialogsWorkspace ? "is-chat-route" : ""} ${isSettings ? "is-settings-route" : ""} ${isProfile ? "is-profile-route" : ""} ${isContacts ? "is-contacts-route" : ""}`}>
        <Sidebar route={route} user={user} setRoute={setRoute} onLogout={onLogout} onSwitchOrganization={onSwitchOrganization} waitingCount={waitingCount} chatScope={chatScope.scope} setChatScope={chatScope.setScope} chatCounters={chatScope.counters} unreadCount={unreadCount} onOpenNotifications={() => { setNotifOpen(true); void loadNotifications(); }} expanded={sidebarExpanded} setExpanded={setSidebarExpanded} />
        <div className="hub-main">
          {manager && <DemoInstallBanner reload={reload} />}
          <UpdateBanner enabled={user.isInstanceAdmin} />
          {/* Верхней панели нет ни у одной роли (дизайн-базлайн v2): заголовок и
              «назад» живут в самой странице, уведомления — в меню профиля сайдбара. */}
          <main className={`hub-scroll ${isDialogsWorkspace ? "sales-dialogs-scroll" : ""} ${isAiFullWidth ? "ai-fullwidth-scroll" : ""} ${isSettings ? "settings-scroll" : ""} ${isProfile ? "profile-scroll" : ""} ${isContacts ? "contacts-scroll" : ""} ${isAgents ? "agents-scroll" : ""} ${isEmployees ? "employees-scroll" : ""} ${isAudit ? "audit-scroll" : ""} ${isPortals ? "portals-scroll" : ""} ${isKnowledge || isKnowledgeEditor ? "knowledge-scroll" : ""}`}>
            <div key={route} className={`hub-page enter-surface ${isSalesWorkspace || isSupportWorkspace ? "sales-workspace-page" : ""} ${isDialogsWorkspace ? "sales-dialogs-page" : ""} ${isAiFullWidth ? "ai-fullwidth-page" : ""} ${isSettings ? "settings-page" : ""} ${isProfile ? "profile-page-shell" : ""} ${isContacts ? "contacts-page-shell" : ""} ${isAgents ? "agents-page-shell" : ""} ${isEmployees ? "employees-page-shell" : ""} ${isAudit ? "audit-page-shell" : ""} ${isKnowledge ? "knowledge-page-shell" : ""} ${isKnowledgeEditor ? "knowledge-editor-shell" : ""} ${isPortals ? "portals-page-shell" : ""}`}>
              <ShellRouteContent settingsSection={settingsSection} openSettings={openSettingsRoute} chatScope={chatScope.scope} setChatScope={chatScope.setScope} chatCounters={chatScope.counters} chatScopeSwitcher={manager} route={route} data={data} selectedEmployeeId={selectedEmployeeId} selectedAgentId={selectedAgentId} selectedKnowledgeId={selectedKnowledgeId} selectedConversationId={selectedConversationId} selectedClientId={selectedClientId} openClient={openClientRoute} selectedChannelId={selectedChannelId} openChannel={openChannelRoute} selectedIntegrationId={selectedIntegrationId} openWebIntegration={openWebIntegrationRoute} openServiceConnection={openServiceConnectionRoute} selectedSupportPortalId={selectedSupportPortalId} portalSettingsSection={portalSettingsSection} openSupportPortal={openSupportPortalRoute} openPortalSettings={openPortalSettingsRoute} openConversation={openConversationRoute} openEmployee={openEmployee} openAgent={openAgentRoute} openKnowledge={openKnowledgeRoute} openKnowledgeEditor={openKnowledgeEditorRoute} onAgentLoaded={() => undefined} onChannelLoaded={() => undefined} reload={reload} setRoute={setRoute} user={user} onUserUpdated={onUserUpdated} onLogout={onLogout} onOpenSidebar={() => setSidebarExpanded(true)} onOrganizationCreated={onOrganizationCreated} />
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
        {notificationAlerts.holder}
        <OnboardingOverlay />
        <OnboardingTour />
        <OnboardingLauncher />
      </div>
    </OnboardingProvider>
  );
}

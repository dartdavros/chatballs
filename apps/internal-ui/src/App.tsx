import { ConfigProvider } from "antd";
import enUS from "antd/locale/en_US";
import ruRU from "antd/locale/ru_RU";
import { useCallback, useEffect, useMemo, useState } from "react";

import { buildTheme } from "@chatballs/ui";

import { applyAppearance, DEFAULT_ACCENT, resolvedDark } from "./shared/appearance";

import { acceptServerLanguage, language } from "./i18n";
import { api, setActiveOrganization } from "./api/client";
import { fetchAgentDirectory } from "./features/agents/model";
import { canAccess, defaultRoute, isManager } from "./auth/access";
import { activateOrganization, clearOrganizationPreference } from "./auth/session";
import { AuthChangePassword, AuthJoin, AuthJoinGuest, AuthLogin, AuthPasswordRecovery, AuthResetPassword, AuthSetup, AuthTotpCode, AuthTotpSetup } from "./features/auth/AuthScreens";
import { Shell } from "./layout/Shell";
import { pathFromRoute, routeFromPath } from "./router";
import { ErrorScreen, LoadingScreen, PermissionScreen } from "./shared/ui";
import { useRouteNavigation } from "./useRouteNavigation";
import type { AgentRef } from "./features/agents/model";
import type { AppData, AuthChallenge, AuthenticatedUser, EmployeeGroup, SessionUser } from "./types";

export function App() {
  const initialRoute = useMemo(() => routeFromPath(window.location.pathname, window.location.search), []);
  const [sessionLoading, setSessionLoading] = useState(true);
  const [identity, setIdentity] = useState<AuthenticatedUser | null>(null);
  const appearanceTheme = identity?.uiTheme ?? "SYSTEM";
  const appearanceAccent = identity?.uiAccent || DEFAULT_ACCENT;
  useEffect(() => {
    applyAppearance(appearanceTheme, appearanceAccent);
  }, [appearanceTheme, appearanceAccent]);
  const antdTheme = useMemo(
    () => buildTheme(resolvedDark(appearanceTheme), appearanceAccent),
    [appearanceTheme, appearanceAccent],
  );
  // Свои строки antd — «Нет данных», подписи пагинации, календарь — берёт из
  // собственных каталогов, и без locale остаётся английским посреди русского
  // экрана. Язык здесь уже окончательный: смена приходит перезагрузкой.
  const antdLocale = language() === "en" ? enUS : ruRU;
  const [user, setUser] = useState<SessionUser | null>(null);
  const [organizationPublicId, setOrganizationPublicId] = useState<string | null>(initialRoute.organizationPublicId);
  const [totpChallenge, setTotpChallenge] = useState<AuthChallenge | null>(null);
  const [recovering, setRecovering] = useState(false);
  const [resetting, setResetting] = useState(() => window.location.pathname === "/reset-password");
  // Ссылка из письма-приглашения (/join?token=…): токен запоминается до входа
  // и принимается, как только известна учётная запись.
  const [joinToken, setJoinToken] = useState<string | null>(
    () => (window.location.pathname === "/join" ? new URLSearchParams(window.location.search).get("token") : null),
  );
  // До входа ссылка ведёт либо на форму создания пароля (учётной записи ещё
  // нет), либо на обычный вход — это решает предпросмотр приглашения.
  const [joinNeedsLogin, setJoinNeedsLogin] = useState(false);
  // Мастер первого запуска: пока в инстансе нет организации, вместо входа — форма создания.
  const [needsSetup, setNeedsSetup] = useState(false);
  const [data, setData] = useState<AppData>({ groups: [], agents: [] });
  const [dataError, setDataError] = useState(false);
  const navigation = useRouteNavigation(initialRoute, organizationPublicId);
  const { navigate } = navigation;

  const useIdentity = useCallback((nextIdentity: AuthenticatedUser, requestedId: string | null) => {
    // Язык приходит уже разрешённым сервером. Если он разошёлся с тем, на
    // котором отрисован экран, страница перезагрузится — иначе половина
    // подписей осталась бы на прежнем языке (см. комментарий в src/i18n).
    acceptServerLanguage(nextIdentity.language);
    const activeUser = activateOrganization(nextIdentity, requestedId);
    setIdentity(nextIdentity);
    setUser(activeUser);
    setOrganizationPublicId(activeUser?.organizationPublicId ?? null);
    setActiveOrganization(activeUser?.organizationPublicId ?? null);
    return activeUser;
  }, []);

  const loadData = useCallback(async () => {
    setDataError(false);
    try {
      // Списки сотрудников и агентов грузят сами страницы — постранично.
      // Здесь остаются только группы: их немного, и они нужны формам и фильтрам
      // по всему приложению.
      const manager = Boolean(user && isManager(user));
      const groups = manager
        ? await api<{ items: EmployeeGroup[] }>("/api/v1/company/groups/")
        : { items: [] };
      let agents: AgentRef[] = [];
      if (user && canAccess(user, "agents")) {
        agents = (await fetchAgentDirectory()).items;
      }
      setData({ groups: groups.items, agents });
    } catch {
      setDataError(true);
    }
  }, [user]);

  useEffect(() => {
    api<{ authenticated: boolean; user?: AuthenticatedUser; language?: string }>("/api/v1/auth/session/")
      .then((payload) => {
        // Язык установки приходит и для гостя: экран входа принадлежит коробке,
        // и на английской машине он должен открываться на языке установки.
        if (!payload.authenticated) acceptServerLanguage(payload.language);
        if (payload.authenticated && payload.user) {
          const activeUser = useIdentity(payload.user, initialRoute.organizationPublicId);
          // Адрес без организации или с чужой: подставляем ту, что открылась.
          if (activeUser && activeUser.organizationPublicId !== initialRoute.organizationPublicId) {
            const nextPath = pathFromRoute(
              initialRoute.route,
              initialRoute.employeeId || initialRoute.agentId || initialRoute.knowledgeId || initialRoute.clientId || initialRoute.channelId || initialRoute.supportPortalId || initialRoute.portalSettingsSection || initialRoute.settingsSection,
              activeUser.organizationPublicId,
            );
            window.history.replaceState({}, "", nextPath);
          }
          return undefined;
        }
        return api<{ needsSetup: boolean }>("/api/v1/setup/").then((setup) => setNeedsSetup(setup.needsSetup));
      })
      .catch(() => undefined)
      .finally(() => setSessionLoading(false));
  }, [initialRoute, useIdentity]);

  useEffect(() => {
    const onPopState = () => {
      const nextRoute = routeFromPath(window.location.pathname, window.location.search);
      if (identity && nextRoute.organizationPublicId !== organizationPublicId) {
        useIdentity(identity, nextRoute.organizationPublicId);
      }
      navigation.applyRouteState(nextRoute);
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [identity, navigation.applyRouteState, organizationPublicId, useIdentity]);

  useEffect(() => {
    if (user) void loadData();
  }, [loadData, user]);

  const landAfterAuth = useCallback((nextIdentity: AuthenticatedUser) => {
    const activeUser = useIdentity(nextIdentity, initialRoute.organizationPublicId);
    if (activeUser) {
      navigate(defaultRoute(activeUser), null, true, activeUser.organizationPublicId);
    }
  }, [initialRoute.organizationPublicId, navigate, useIdentity]);

  const refreshIdentity = useCallback((nextIdentity: AuthenticatedUser) => {
    useIdentity(nextIdentity, organizationPublicId);
  }, [organizationPublicId, useIdentity]);

  // Переключатель в сайдбаре: другая организация открывается со своего
  // стартового экрана, Shell пересобирается по key — состояние страниц
  // прежней организации в новую не переезжает.
  const switchOrganization = useCallback((nextOrganizationId: string) => {
    if (!identity) return;
    const activeUser = useIdentity(identity, nextOrganizationId);
    if (activeUser) {
      navigate(defaultRoute(activeUser), null, false, activeUser.organizationPublicId);
    }
  }, [identity, navigate, useIdentity]);

  const finishJoin = useCallback((nextIdentity: AuthenticatedUser, organizationId: string) => {
    setJoinToken(null);
    const activeUser = useIdentity(nextIdentity, organizationId);
    if (activeUser) {
      navigate(defaultRoute(activeUser), null, true, activeUser.organizationPublicId);
    }
  }, [navigate, useIdentity]);

  const joinUseLogin = useCallback(() => setJoinNeedsLogin(true), []);

  const cancelJoin = useCallback(() => {
    setJoinToken(null);
    if (user) navigate(defaultRoute(user), null, true, user.organizationPublicId);
  }, [navigate, user]);

  async function logout() {
    await api("/api/v1/auth/logout/", { method: "POST" }).catch(() => undefined);
    setIdentity(null);
    setUser(null);
    setOrganizationPublicId(null);
    setActiveOrganization(null);
    clearOrganizationPreference();
    setTotpChallenge(null);
    navigate("chat", null, true, null);
    setData({ groups: [], agents: [] });
  }

  if (resetting) {
    return (
      <ConfigProvider theme={antdTheme} locale={antdLocale}>
        <AuthResetPassword onDone={() => { setResetting(false); window.history.replaceState({}, "", pathFromRoute("chat")); }} />
      </ConfigProvider>
    );
  }

  if (sessionLoading) return <ConfigProvider theme={antdTheme} locale={antdLocale}><LoadingScreen /></ConfigProvider>;

  return (
    <ConfigProvider theme={antdTheme} locale={antdLocale}>
      {totpChallenge ? (
        <AuthTotpCode challenge={totpChallenge} onVerified={(nextUser) => { setTotpChallenge(null); landAfterAuth(nextUser); }} />
      ) : !identity ? (
        joinToken && !joinNeedsLogin && !needsSetup ? (
          <AuthJoinGuest token={joinToken} onUseLogin={joinUseLogin} onRegistered={finishJoin} />
        ) : needsSetup ? (
          <AuthSetup onDone={(nextUser) => { setNeedsSetup(false); landAfterAuth(nextUser); }} />
        ) : recovering ? (
          <AuthPasswordRecovery onBackToLogin={() => setRecovering(false)} />
        ) : (
          <AuthLogin onLogin={landAfterAuth} onTotpChallenge={setTotpChallenge} onRecover={() => setRecovering(true)} />
        )
      ) : joinToken ? (
        <AuthJoin token={joinToken} onAccepted={finishJoin} onBack={cancelJoin} />
      ) : !user ? (
        <PermissionScreen onReturn={logout} />
      ) : user.mustChangePassword ? (
        <AuthChangePassword user={user} onChanged={landAfterAuth} />
      ) : user.totpRequired && !user.totpEnabled ? (
        <AuthTotpSetup user={user} onConfirmed={landAfterAuth} />
      ) : dataError ? (
        <ErrorScreen retry={loadData} />
      ) : !canAccess(user, navigation.route) ? (
        <PermissionScreen onReturn={() => navigate(defaultRoute(user), null, true)} />
      ) : (
        <Shell key={user.organizationPublicId} route={navigation.route} setRoute={(nextRoute) => navigate(nextRoute)} selectedEmployeeId={navigation.selectedEmployeeId} selectedAgentId={navigation.selectedAgentId} selectedKnowledgeId={navigation.selectedKnowledgeId} selectedConversationId={navigation.selectedConversationId} selectedClientId={navigation.selectedClientId} openClientRoute={(clientId) => navigate("salesClientDetail", clientId)} selectedChannelId={navigation.selectedChannelId} openChannelRoute={(channelId) => navigate("agentDetail", channelId)} selectedSupportPortalId={navigation.selectedSupportPortalId} openSupportPortalRoute={(portalId) => navigate("supportPortalDetail", portalId)} portalSettingsSection={navigation.selectedPortalSection} openPortalSettingsRoute={(portalId, section) => navigate("supportPortalSettings", `${portalId}/${section ?? ""}`)} settingsSection={navigation.selectedSettingsSection} openSettingsRoute={(section) => navigate("settings", section)} openEmployeeRoute={(employeeId) => navigate("employeeDetail", employeeId)} openAgentRoute={(agentId) => navigate("agentDetail", agentId)} openKnowledgeRoute={(knowledgeId) => navigate("knowledgeDetail", knowledgeId)} openKnowledgeEditorRoute={(knowledgeId) => (knowledgeId === null ? navigate("knowledgeCreate") : navigate("knowledgeEdit", knowledgeId))} openConversationRoute={(conversationId) => navigate("chat", conversationId)} user={user} data={data} reload={loadData} onUserUpdated={refreshIdentity} onLogout={logout} onSwitchOrganization={switchOrganization} />
      )}
    </ConfigProvider>
  );
}

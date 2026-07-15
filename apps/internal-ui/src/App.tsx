import { ConfigProvider } from "antd";
import { useCallback, useEffect, useMemo, useState } from "react";

import { edevsHubTheme } from "@edevs/ui";

import { api, setActiveOrganization } from "./api/client";
import { canAccess, defaultRoute } from "./auth/access";
import { activateOrganization, clearOrganizationPreference } from "./auth/session";
import { AuthChangePassword, AuthLogin, AuthPasswordRecovery, AuthResetPassword, AuthTotpCode, AuthTotpSetup } from "./features/auth/AuthScreens";
import { Shell } from "./layout/Shell";
import { pathFromRoute, routeFromPath } from "./router";
import { ErrorScreen, LoadingScreen, PermissionScreen } from "./shared/ui";
import { useRouteNavigation } from "./useRouteNavigation";
import type { AiAgent } from "./features/ai/model";
import type { AppData, AuthChallenge, AuthenticatedUser, Department, Employee, Product, SessionUser } from "./types";

export function App() {
  const initialRoute = useMemo(() => routeFromPath(window.location.pathname, window.location.search), []);
  const [sessionLoading, setSessionLoading] = useState(true);
  const [identity, setIdentity] = useState<AuthenticatedUser | null>(null);
  const [user, setUser] = useState<SessionUser | null>(null);
  const [organizationPublicId, setOrganizationPublicId] = useState<string | null>(initialRoute.organizationPublicId);
  const [totpChallenge, setTotpChallenge] = useState<AuthChallenge | null>(null);
  const [recovering, setRecovering] = useState(false);
  const [resetting, setResetting] = useState(() => window.location.pathname === "/reset-password");
  const [data, setData] = useState<AppData>({ employees: [], departments: [], products: [], agents: [] });
  const [dataError, setDataError] = useState(false);
  const navigation = useRouteNavigation(initialRoute, organizationPublicId);
  const { navigate } = navigation;

  const useIdentity = useCallback((nextIdentity: AuthenticatedUser, requestedId: string | null) => {
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
      const [employees, departments, products] = await Promise.all([
        user && canAccess(user, "employees")
          ? api<{ items: Employee[] }>("/api/v1/employees/")
          : Promise.resolve({ items: [] }),
        user && canAccess(user, "departments")
          ? api<{ items: Department[] }>("/api/v1/company/departments/")
          : Promise.resolve({ items: [] }),
        user && canAccess(user, "products")
          ? api<{ items: Product[] }>("/api/v1/company/products/")
          : Promise.resolve({ items: [] }),
      ]);
      let agents: AiAgent[] = [];
      if (user && canAccess(user, "aiAgents")) {
        const agentsResponse = await api<{ items: AiAgent[] }>("/api/v1/ai/agents/");
        agents = agentsResponse.items;
      }
      setData({ employees: employees.items, departments: departments.items, products: products.items, agents });
    } catch {
      setDataError(true);
    }
  }, [user]);

  useEffect(() => {
    api<{ authenticated: boolean; user?: AuthenticatedUser }>("/api/v1/auth/session/")
      .then((payload) => {
        if (payload.authenticated && payload.user) {
          const activeUser = useIdentity(payload.user, initialRoute.organizationPublicId);
          if (activeUser && !initialRoute.organizationPublicId) {
            const nextPath = pathFromRoute(
              initialRoute.route,
              initialRoute.employeeId || initialRoute.productId || initialRoute.agentId || initialRoute.knowledgeId || initialRoute.clientId || initialRoute.orderId,
              initialRoute.productCode,
              activeUser.organizationPublicId,
            );
            window.history.replaceState({}, "", nextPath);
          }
        }
      })
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
      navigate(defaultRoute(activeUser), null, true, null, activeUser.organizationPublicId);
    }
  }, [initialRoute.organizationPublicId, navigate, useIdentity]);

  const refreshIdentity = useCallback((nextIdentity: AuthenticatedUser) => {
    useIdentity(nextIdentity, organizationPublicId);
  }, [organizationPublicId, useIdentity]);

  async function logout() {
    await api("/api/v1/auth/logout/", { method: "POST" }).catch(() => undefined);
    setIdentity(null);
    setUser(null);
    setOrganizationPublicId(null);
    setActiveOrganization(null);
    clearOrganizationPreference();
    setTotpChallenge(null);
    navigate("command", null, true, null, null);
    setData({ employees: [], departments: [], products: [], agents: [] });
  }

  if (resetting) {
    return (
      <ConfigProvider theme={edevsHubTheme}>
        <AuthResetPassword onDone={() => { setResetting(false); window.history.replaceState({}, "", pathFromRoute("command")); }} />
      </ConfigProvider>
    );
  }

  if (sessionLoading) return <ConfigProvider theme={edevsHubTheme}><LoadingScreen /></ConfigProvider>;

  return (
    <ConfigProvider theme={edevsHubTheme}>
      {totpChallenge ? (
        <AuthTotpCode challenge={totpChallenge} onVerified={(nextUser) => { setTotpChallenge(null); landAfterAuth(nextUser); }} />
      ) : !identity ? (
        recovering ? (
          <AuthPasswordRecovery onBackToLogin={() => setRecovering(false)} />
        ) : (
          <AuthLogin onLogin={landAfterAuth} onTotpChallenge={setTotpChallenge} onRecover={() => setRecovering(true)} />
        )
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
        <Shell route={navigation.route} setRoute={(nextRoute) => navigate(nextRoute)} selectedEmployeeId={navigation.selectedEmployeeId} selectedProductId={navigation.selectedProductId} selectedProductCode={navigation.selectedProductCode} selectedAgentId={navigation.selectedAgentId} selectedKnowledgeId={navigation.selectedKnowledgeId} selectedConversationId={navigation.selectedConversationId} selectedClientId={navigation.selectedClientId} openClientRoute={(clientId) => navigate("salesClientDetail", clientId)} selectedOrderId={navigation.selectedOrderId} openOrderRoute={(orderId) => navigate("salesOrderDetail", orderId)} openEmployeeRoute={(employeeId) => navigate("employeeDetail", employeeId)} openProductRoute={(productId) => navigate("productDetail", productId)} openAgentCreateRoute={(productCode) => navigate("aiAgentCreate", null, false, productCode)} openAgentRoute={(agentId) => navigate("aiAgentDetail", agentId)} openKnowledgeRoute={(knowledgeId) => navigate("aiKnowledgeDetail", knowledgeId)} openConversationRoute={(conversationId) => navigate("salesDialogs", conversationId)} user={user} data={data} reload={loadData} onUserUpdated={refreshIdentity} onLogout={logout} />
      )}
    </ConfigProvider>
  );
}

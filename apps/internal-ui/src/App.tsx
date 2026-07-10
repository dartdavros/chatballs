import { ConfigProvider } from "antd";
import { useCallback, useEffect, useMemo, useState } from "react";

import { edevsHubTheme } from "@edevs/ui";

import { api } from "./api/client";
import { canAccess, defaultRoute } from "./auth/access";
import { AuthChangePassword, AuthLogin, AuthPasswordRecovery, AuthResetPassword, AuthTotpCode, AuthTotpSetup } from "./features/auth/AuthScreens";
import { Shell } from "./layout/Shell";
import { pathFromRoute, routeFromPath } from "./router";
import { ErrorScreen, LoadingScreen, PermissionScreen } from "./shared/ui";
import type { AiAgent } from "./features/ai/model";
import type { AppData, AuthChallenge, Department, Employee, Product, RouteKey, SessionUser } from "./types";

export function App() {
  const initialRoute = useMemo(() => routeFromPath(window.location.pathname, window.location.search), []);
  const [sessionLoading, setSessionLoading] = useState(true);
  const [user, setUser] = useState<SessionUser | null>(null);
  const [totpChallenge, setTotpChallenge] = useState<AuthChallenge | null>(null);
  const [recovering, setRecovering] = useState(false);
  const [resetting, setResetting] = useState(() => window.location.pathname === "/reset-password");
  const [route, setRoute] = useState<RouteKey>(initialRoute.route);
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<number | null>(initialRoute.employeeId);
  const [selectedProductId, setSelectedProductId] = useState<number | null>(initialRoute.productId);
  const [selectedProductCode, setSelectedProductCode] = useState<string | null>(initialRoute.productCode);
  const [selectedAgentId, setSelectedAgentId] = useState<number | null>(initialRoute.agentId);
  const [selectedKnowledgeId, setSelectedKnowledgeId] = useState<number | null>(initialRoute.knowledgeId);
  const [selectedConversationId, setSelectedConversationId] = useState<number | null>(null);
  const [selectedClientId, setSelectedClientId] = useState<number | null>(initialRoute.clientId);
  const [selectedOrderId, setSelectedOrderId] = useState<number | null>(initialRoute.orderId);
  const [data, setData] = useState<AppData>({ employees: [], departments: [], products: [], agents: [] });
  const [dataError, setDataError] = useState(false);

  const navigate = useCallback((nextRoute: RouteKey, entityId: number | null = null, replace = false, productCode: string | null = null) => {
    const nextEmployeeId = nextRoute === "employeeDetail" ? entityId : null;
    const nextProductId = nextRoute === "productDetail" ? entityId : null;
    const nextProductCode = nextRoute === "aiAgentCreate" ? productCode : null;
    const nextAgentId = nextRoute === "aiAgentDetail" ? entityId : null;
    const nextKnowledgeId = nextRoute === "aiKnowledgeDetail" ? entityId : null;
    const nextConversationId = nextRoute === "salesDialogs" || nextRoute === "supportDialogs" ? entityId : null;
    const nextClientId = nextRoute === "salesClientDetail" ? entityId : null;
    const nextOrderId = nextRoute === "salesOrderDetail" ? entityId : null;
    const nextPath = pathFromRoute(nextRoute, entityId, nextProductCode);
    setRoute(nextRoute);
    setSelectedEmployeeId(nextEmployeeId);
    setSelectedProductId(nextProductId);
    setSelectedProductCode(nextProductCode);
    setSelectedAgentId(nextAgentId);
    setSelectedKnowledgeId(nextKnowledgeId);
    setSelectedConversationId(nextConversationId);
    setSelectedClientId(nextClientId);
    setSelectedOrderId(nextOrderId);
    if (`${window.location.pathname}${window.location.search}` !== nextPath) {
      const state = { route: nextRoute, employeeId: nextEmployeeId, productId: nextProductId, productCode: nextProductCode, agentId: nextAgentId, knowledgeId: nextKnowledgeId };
      if (replace) {
        window.history.replaceState(state, "", nextPath);
      } else {
        window.history.pushState(state, "", nextPath);
      }
    }
  }, []);

  const loadData = useCallback(async () => {
    setDataError(false);
    try {
      const [employees, departments, products] = await Promise.all([
        api<{ items: Employee[] }>("/api/v1/employees/"),
        api<{ items: Department[] }>("/api/v1/company/departments/"),
        api<{ items: Product[] }>("/api/v1/company/products/"),
      ]);
      let agents: AiAgent[] = [];
      if (user?.role === "OWNER") {
        const agentsResponse = await api<{ items: AiAgent[] }>("/api/v1/ai/agents/");
        agents = agentsResponse.items;
      }
      setData({ employees: employees.items, departments: departments.items, products: products.items, agents });
    } catch {
      setDataError(true);
    }
  }, [user?.role]);

  useEffect(() => {
    api<{ authenticated: boolean; user?: SessionUser }>("/api/v1/auth/session/")
      .then((payload) => {
        if (payload.authenticated && payload.user) {
          setUser(payload.user);
        }
      })
      .finally(() => setSessionLoading(false));
  }, []);

  useEffect(() => {
    const onPopState = () => {
      const nextRoute = routeFromPath(window.location.pathname, window.location.search);
      setRoute(nextRoute.route);
      setSelectedEmployeeId(nextRoute.employeeId);
      setSelectedProductId(nextRoute.productId);
      setSelectedProductCode(nextRoute.productCode);
      setSelectedAgentId(nextRoute.agentId);
      setSelectedKnowledgeId(nextRoute.knowledgeId);
      setSelectedClientId(nextRoute.clientId);
      setSelectedOrderId(nextRoute.orderId);
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    if (user) void loadData();
  }, [loadData, user]);

  const landAfterAuth = useCallback((nextUser: SessionUser) => {
    setUser(nextUser);
    navigate(defaultRoute(nextUser.role, nextUser.department), null, true);
  }, [navigate]);

  async function logout() {
    await api("/api/v1/auth/logout/", { method: "POST" }).catch(() => undefined);
    setUser(null);
    setTotpChallenge(null);
    navigate("command", null, true);
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
      ) : !user ? (
        recovering ? (
          <AuthPasswordRecovery onBackToLogin={() => setRecovering(false)} />
        ) : (
          <AuthLogin onLogin={landAfterAuth} onTotpChallenge={setTotpChallenge} onRecover={() => setRecovering(true)} />
        )
      ) : user.mustChangePassword ? (
        <AuthChangePassword user={user} onChanged={setUser} />
      ) : user.totpRequired && !user.totpEnabled ? (
        <AuthTotpSetup user={user} onConfirmed={setUser} />
      ) : dataError ? (
        <ErrorScreen retry={loadData} />
      ) : !canAccess(user.role, route, user.department) ? (
        <PermissionScreen onReturn={() => navigate(defaultRoute(user.role, user.department), null, true)} />
      ) : (
        <Shell route={route} setRoute={(nextRoute) => navigate(nextRoute)} selectedEmployeeId={selectedEmployeeId} selectedProductId={selectedProductId} selectedProductCode={selectedProductCode} selectedAgentId={selectedAgentId} selectedKnowledgeId={selectedKnowledgeId} selectedConversationId={selectedConversationId} selectedClientId={selectedClientId} openClientRoute={(clientId) => navigate("salesClientDetail", clientId)} selectedOrderId={selectedOrderId} openOrderRoute={(orderId) => navigate("salesOrderDetail", orderId)} openEmployeeRoute={(employeeId) => navigate("employeeDetail", employeeId)} openProductRoute={(productId) => navigate("productDetail", productId)} openAgentCreateRoute={(productCode) => navigate("aiAgentCreate", null, false, productCode)} openAgentRoute={(agentId) => navigate("aiAgentDetail", agentId)} openKnowledgeRoute={(knowledgeId) => navigate("aiKnowledgeDetail", knowledgeId)} openConversationRoute={(conversationId) => navigate("salesDialogs", conversationId)} user={user} data={data} reload={loadData} onUserUpdated={setUser} onLogout={logout} />
      )}
    </ConfigProvider>
  );
}

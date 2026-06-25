import { ConfigProvider } from "antd";
import { useCallback, useEffect, useMemo, useState } from "react";

import { edevsHubTheme } from "@edevs/ui";

import { api } from "./api/client";
import { canAccess, defaultRoute } from "./auth/access";
import { AuthChangePassword, AuthLogin, AuthPasswordRecovery, AuthResetPassword, AuthTotpCode, AuthTotpSetup } from "./features/auth/AuthScreens";
import { Shell } from "./layout/Shell";
import { pathFromRoute, routeFromPath } from "./router";
import { ErrorScreen, LoadingScreen, PermissionScreen } from "./shared/ui";
import type { AppData, AuthChallenge, Department, Employee, Product, RouteKey, SessionUser } from "./types";

export function App() {
  const initialRoute = useMemo(() => routeFromPath(window.location.pathname), []);
  const [sessionLoading, setSessionLoading] = useState(true);
  const [user, setUser] = useState<SessionUser | null>(null);
  const [totpChallenge, setTotpChallenge] = useState<AuthChallenge | null>(null);
  const [recovering, setRecovering] = useState(false);
  const [resetting, setResetting] = useState(() => window.location.pathname === "/reset-password");
  const [route, setRoute] = useState<RouteKey>(initialRoute.route);
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<number | null>(initialRoute.employeeId);
  const [selectedProductId, setSelectedProductId] = useState<number | null>(initialRoute.productId);
  const [selectedAgentId, setSelectedAgentId] = useState<number | null>(initialRoute.agentId);
  const [selectedReleaseId, setSelectedReleaseId] = useState<number | null>(initialRoute.releaseId);
  const [data, setData] = useState<AppData>({ employees: [], departments: [], products: [] });
  const [dataError, setDataError] = useState(false);

  const navigate = useCallback((nextRoute: RouteKey, entityId: number | null = null, replace = false) => {
    const nextEmployeeId = nextRoute === "employeeDetail" ? entityId : null;
    const nextProductId = nextRoute === "productDetail" ? entityId : null;
    const nextAgentId = nextRoute === "aiAgentDetail" ? entityId : null;
    const nextReleaseId = nextRoute === "aiRelease" ? entityId : null;
    const nextPath = pathFromRoute(nextRoute, entityId);
    setRoute(nextRoute);
    setSelectedEmployeeId(nextEmployeeId);
    setSelectedProductId(nextProductId);
    setSelectedAgentId(nextAgentId);
    setSelectedReleaseId(nextReleaseId);
    if (window.location.pathname !== nextPath) {
      const state = { route: nextRoute, employeeId: nextEmployeeId, productId: nextProductId, agentId: nextAgentId, releaseId: nextReleaseId };
      if (replace) {
        window.history.replaceState(state, "", nextPath);
      } else {
        window.history.pushState(state, "", nextPath);
      }
    }
  }, []);

  const loadData = useMemo(() => async () => {
    setDataError(false);
    try {
      const [employees, departments, products] = await Promise.all([
        api<{ items: Employee[] }>("/api/v1/employees/"),
        api<{ items: Department[] }>("/api/v1/company/departments/"),
        api<{ items: Product[] }>("/api/v1/company/products/"),
      ]);
      setData({ employees: employees.items, departments: departments.items, products: products.items });
    } catch {
      setDataError(true);
    }
  }, []);

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
      const nextRoute = routeFromPath(window.location.pathname);
      setRoute(nextRoute.route);
      setSelectedEmployeeId(nextRoute.employeeId);
      setSelectedProductId(nextRoute.productId);
      setSelectedAgentId(nextRoute.agentId);
      setSelectedReleaseId(nextRoute.releaseId);
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    if (user) void loadData();
  }, [loadData, user]);

  const landAfterAuth = useCallback((nextUser: SessionUser) => {
    setUser(nextUser);
    navigate(defaultRoute(nextUser.role), null, true);
  }, [navigate]);

  async function logout() {
    await api("/api/v1/auth/logout/", { method: "POST" }).catch(() => undefined);
    setUser(null);
    setTotpChallenge(null);
    navigate("command", null, true);
    setData({ employees: [], departments: [], products: [] });
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
      ) : !canAccess(user.role, route) ? (
        <PermissionScreen onReturn={() => navigate(defaultRoute(user.role), null, true)} />
      ) : (
        <Shell route={route} setRoute={(nextRoute) => navigate(nextRoute)} selectedEmployeeId={selectedEmployeeId} selectedProductId={selectedProductId} selectedAgentId={selectedAgentId} selectedReleaseId={selectedReleaseId} openEmployeeRoute={(employeeId) => navigate("employeeDetail", employeeId)} openProductRoute={(productId) => navigate("productDetail", productId)} openAgentRoute={(agentId) => navigate("aiAgentDetail", agentId)} openReleaseRoute={(releaseId) => navigate("aiRelease", releaseId)} user={user} data={data} reload={loadData} onUserUpdated={setUser} onLogout={logout} />
      )}
    </ConfigProvider>
  );
}

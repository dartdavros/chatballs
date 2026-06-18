import { ConfigProvider } from "antd";
import { useCallback, useEffect, useMemo, useState } from "react";

import { edevsHubTheme } from "@edevs/ui";

import { api } from "./api/client";
import { AuthChangePassword, AuthLogin, AuthTotpCode, AuthTotpSetup } from "./features/auth/AuthScreens";
import { Shell } from "./layout/Shell";
import { pathFromRoute, routeFromPath } from "./router";
import { ErrorScreen, LoadingScreen } from "./shared/ui";
import type { AppData, AuthChallenge, Department, Employee, Product, RouteKey, SessionUser } from "./types";

export function App() {
  const initialRoute = useMemo(() => routeFromPath(window.location.pathname), []);
  const [sessionLoading, setSessionLoading] = useState(true);
  const [user, setUser] = useState<SessionUser | null>(null);
  const [totpChallenge, setTotpChallenge] = useState<AuthChallenge | null>(null);
  const [route, setRoute] = useState<RouteKey>(initialRoute.route);
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<number | null>(initialRoute.employeeId);
  const [data, setData] = useState<AppData>({ employees: [], departments: [], products: [] });
  const [dataError, setDataError] = useState(false);

  const navigate = useCallback((nextRoute: RouteKey, employeeId: number | null = null, replace = false) => {
    const nextEmployeeId = nextRoute === "employeeDetail" ? employeeId : null;
    const nextPath = pathFromRoute(nextRoute, nextEmployeeId);
    setRoute(nextRoute);
    setSelectedEmployeeId(nextEmployeeId);
    if (window.location.pathname !== nextPath) {
      const state = { route: nextRoute, employeeId: nextEmployeeId };
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
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    if (user) void loadData();
  }, [loadData, user]);

  async function logout() {
    await api("/api/v1/auth/logout/", { method: "POST" }).catch(() => undefined);
    setUser(null);
    setTotpChallenge(null);
    navigate("command", null, true);
    setData({ employees: [], departments: [], products: [] });
  }

  if (sessionLoading) return <ConfigProvider theme={edevsHubTheme}><LoadingScreen /></ConfigProvider>;

  return (
    <ConfigProvider theme={edevsHubTheme}>
      {totpChallenge ? (
        <AuthTotpCode challenge={totpChallenge} onVerified={(nextUser) => { setTotpChallenge(null); setUser(nextUser); }} />
      ) : !user ? (
        <AuthLogin onLogin={(nextUser) => { setUser(nextUser); void loadData(); }} onTotpChallenge={setTotpChallenge} />
      ) : user.mustChangePassword ? (
        <AuthChangePassword user={user} onChanged={setUser} />
      ) : user.totpRequired && !user.totpEnabled ? (
        <AuthTotpSetup user={user} onConfirmed={setUser} />
      ) : dataError ? (
        <ErrorScreen retry={loadData} />
      ) : (
        <Shell route={route} setRoute={(nextRoute) => navigate(nextRoute)} selectedEmployeeId={selectedEmployeeId} openEmployeeRoute={(employeeId) => navigate("employeeDetail", employeeId)} user={user} data={data} reload={loadData} onUserUpdated={setUser} onLogout={logout} />
      )}
    </ConfigProvider>
  );
}

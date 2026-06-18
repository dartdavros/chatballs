import { ConfigProvider } from "antd";
import { useEffect, useMemo, useState } from "react";

import { edevsHubTheme } from "@edevs/ui";

import { api } from "./api/client";
import { AuthChangePassword, AuthLogin, AuthTotpCode, AuthTotpSetup } from "./features/auth/AuthScreens";
import { Shell } from "./layout/Shell";
import { ErrorScreen, LoadingScreen } from "./shared/ui";
import type { AppData, AuthChallenge, Department, Employee, Product, RouteKey, SessionUser } from "./types";

export function App() {
  const [sessionLoading, setSessionLoading] = useState(true);
  const [user, setUser] = useState<SessionUser | null>(null);
  const [totpChallenge, setTotpChallenge] = useState<AuthChallenge | null>(null);
  const [route, setRoute] = useState<RouteKey>("command");
  const [data, setData] = useState<AppData>({ employees: [], departments: [], products: [] });
  const [dataError, setDataError] = useState(false);

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
    if (user) void loadData();
  }, [loadData, user]);

  async function logout() {
    await api("/api/v1/auth/logout/", { method: "POST" }).catch(() => undefined);
    setUser(null);
    setTotpChallenge(null);
    setRoute("command");
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
        <Shell route={route} setRoute={setRoute} user={user} data={data} reload={loadData} onUserUpdated={setUser} onLogout={logout} />
      )}
    </ConfigProvider>
  );
}

import type { RouteKey } from "./types";

export type RouteState = {
  route: RouteKey;
  employeeId: number | null;
};

export function routeFromPath(pathname: string): RouteState {
  const path = pathname.replace(/\/+$/, "") || "/";
  if (path === "/" || path === "/command") return { route: "command", employeeId: null };
  if (path === "/departments") return { route: "departments", employeeId: null };
  if (path === "/departments/sales") return { route: "salesOverview", employeeId: null };
  if (path === "/departments/sales/clients") return { route: "salesClients", employeeId: null };
  if (path === "/departments/sales/dialogs") return { route: "salesDialogs", employeeId: null };
  if (path === "/employees") return { route: "employees", employeeId: null };
  if (path.startsWith("/employees/")) {
    const id = Number(path.split("/")[2]);
    return Number.isInteger(id) && id > 0 ? { route: "employeeDetail", employeeId: id } : { route: "employees", employeeId: null };
  }
  if (path === "/products") return { route: "products", employeeId: null };
  if (path === "/profile") return { route: "profile", employeeId: null };
  return { route: "command", employeeId: null };
}

export function pathFromRoute(route: RouteKey, employeeId: number | null = null): string {
  if (route === "command") return "/";
  if (route === "departments") return "/departments";
  if (route === "salesOverview") return "/departments/sales";
  if (route === "salesClients") return "/departments/sales/clients";
  if (route === "salesDialogs") return "/departments/sales/dialogs";
  if (route === "employees") return "/employees";
  if (route === "employeeDetail") return employeeId ? `/employees/${employeeId}` : "/employees";
  if (route === "products") return "/products";
  return "/profile";
}

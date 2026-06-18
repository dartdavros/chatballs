export type Role = "OWNER" | "OPERATOR";
export type ProductStatus = "ACTIVE" | "DISABLED";

export type SessionUser = {
  id: number;
  email: string;
  fullName: string;
  role: Role;
  organization: string;
  organizationName: string;
  department: string | null;
  mustChangePassword: boolean;
  totpRequired: boolean;
  totpEnabled: boolean;
};

export type AuthChallenge = {
  email: string;
  fullName: string;
  role: Role;
};

export type LoginPayload =
  | { authenticated: true; user: SessionUser }
  | { authenticated: false; totpRequired: true; totpEnabled: true; challenge: AuthChallenge };

export type Employee = {
  id: number;
  email: string;
  fullName: string;
  role: Role;
  phone: string;
  department: string | null;
  isActive: boolean;
  isBlocked: boolean;
  mustChangePassword: boolean;
  totpRequired: boolean;
  totpEnabled: boolean;
};

export type Department = {
  id: number;
  code: string;
  name: string;
  status: string;
  memberCount: number;
  operatorCount: number;
  activeOperatorCount: number;
  products: Array<{ code: string; name: string }>;
};

export type Product = {
  id: number;
  code: string;
  name: string;
  status: ProductStatus;
  siteUrl: string;
  createdAt: string;
};

export type RouteKey = "command" | "departments" | "employeeDetail" | "employees" | "products" | "profile" | "salesOverview";

export type AppData = {
  employees: Employee[];
  departments: Department[];
  products: Product[];
};

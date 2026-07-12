import type { AiAgent } from "./features/ai/model";

// Системные роли ADR-HUB-0027. OPERATOR удалён как системная роль (этап 1);
// «оператор» — рабочая функция сотрудника (EMPLOYEE) в своём отделе.
export type Role = "OWNER" | "ADMIN" | "EMPLOYEE";
export type ProductStatus = "ACTIVE" | "DISABLED";

export type SessionUser = {
  id: number;
  email: string;
  fullName: string;
  role: Role;
  positionTitle: string;
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

// Флаги доступных действий над сотрудником для текущего пользователя. Backend —
// источник истины (ADR-HUB-0027 этап 2); фронтенд скрывает недоступное.
export type EmployeePermissions = {
  canView: boolean;
  canUpdateProfile: boolean;
  canChangeRole: boolean;
  canChangePlacement: boolean;
  canBlock: boolean;
  canUnblock: boolean;
  canResetPassword: boolean;
  canTerminateSessions: boolean;
  canTransferOwnership: boolean;
};

export type Employee = {
  id: number;
  email: string;
  fullName: string;
  role: Role;
  positionTitle: string;
  phone: string;
  department: string | null;
  isActive: boolean;
  isBlocked: boolean;
  mustChangePassword: boolean;
  totpRequired: boolean;
  totpEnabled: boolean;
  permissions?: EmployeePermissions;
};

export type Department = {
  id: number;
  code: string;
  name: string;
  status: string;
  memberCount: number;
  operatorCount: number;
  activeOperatorCount: number;
  agentCount: number;
  products: Array<{ code: string; name: string }>;
};

export type Product = {
  id: number;
  code: string;
  name: string;
  status: ProductStatus;
  siteUrl: string;
  departments: Array<{ id: number; code: string; name: string }>;
  offers: ProductOffer[];
  createdAt: string;
  updatedAt: string;
};

export type ProductPrice = {
  id: number;
  version: number;
  amountMinor: number;
  currency: string;
  billingPeriod: "ONE_TIME" | "MONTH" | "YEAR";
  validFrom: string;
  validUntil: string | null;
  isActive: boolean;
};

export type ProductOffer = {
  id: number;
  code: string;
  name: string;
  description: string;
  fulfillmentType: "SAAS_ACCESS" | "BOX_LICENSE" | "SUPPORT_EXTENSION";
  paymentType: "ONE_TIME" | "SUBSCRIPTION";
  primaryBoxOfferId: number | null;
  isActive: boolean;
  aiOfferable: boolean;
  fiscalName: string;
  accessSchema: Record<string, unknown>;
  prices: ProductPrice[];
};

export type RouteKey = "command" | "departments" | "employeeDetail" | "employees" | "productDetail" | "products" | "profile" | "salesClientDetail" | "salesClients" | "salesDialogs" | "salesOrderDetail" | "salesOrders" | "salesOverview" | "supportOverview" | "supportDialogs" | "aiAgents" | "aiAgentCreate" | "aiAgentDetail" | "aiKnowledge" | "aiKnowledgeDetail" | "aiUsage" | "integrations";

export type AppData = {
  employees: Employee[];
  departments: Department[];
  products: Product[];
  agents: AiAgent[];
};

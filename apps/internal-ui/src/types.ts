import type { AgentCard } from "./features/agents/model";

// Роли SPEC-HUB-0031 §3: OWNER и ADMIN идентичны (владельца нельзя удалить),
// EMPLOYEE работает только в чате; видимость диалогов — по группам (ADR-HUB-0043).
export type Role = "OWNER" | "ADMIN" | "EMPLOYEE";
export type ProductStatus = "ACTIVE" | "DISABLED";
export type DeliveryMode = "CLOUD" | "SELF_HOSTED";

export type EmployeeGroupRef = {
  id: number;
  name: string;
};

export type EmployeeGroup = EmployeeGroupRef & {
  memberCount: number;
  memberIds: number[];
  createdAt: string;
};

export type OrganizationMembership = {
  id: number;
  organizationPublicId: string;
  role: Role;
  positionTitle: string;
  organization: string;
  organizationName: string;
  organizationLogoUrl: string | null;
  totpRequired: boolean;
  capabilities: string[];
  groups: EmployeeGroupRef[];
};

export type AuthenticatedUser = {
  id: number;
  email: string;
  fullName: string;
  mustChangePassword: boolean;
  totpEnabled: boolean;
  deliveryMode: DeliveryMode;
  memberships: OrganizationMembership[];
};

export type SessionUser = AuthenticatedUser & OrganizationMembership;

export type AuthChallenge = {
  email: string;
  fullName: string;
};

export type LoginPayload =
  | { authenticated: true; user: AuthenticatedUser }
  | { authenticated: false; totpRequired: true; totpEnabled: true; challenge: AuthChallenge };

// Флаги доступных действий над сотрудником для текущего пользователя. Backend —
// источник истины (SPEC-HUB-0031 §3); фронтенд скрывает недоступное.
export type EmployeePermissions = {
  canView: boolean;
  canUpdateProfile: boolean;
  canChangeRole: boolean;
  canChangeGroups: boolean;
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
  groups: EmployeeGroupRef[];
  createdAt?: string;
  lastLogin?: string | null;
  isActive: boolean;
  isBlocked: boolean;
  mustChangePassword: boolean;
  totpRequired: boolean;
  totpEnabled: boolean;
  permissions?: EmployeePermissions;
  activeSessionCount?: number;
  auditEvents?: EmployeeAuditEvent[];
};

export type EmployeeAuditEvent = {
  action: string;
  result: string;
  createdAt: string;
};

export type ProductChannelRef = {
  id: number;
  code: string;
  name: string;
  isActive: boolean;
  agentId: number | null;
  // provider/status — значения enum интеграций (см. features/integrations/model.ts);
  // объявлены литералами, чтобы корневой тип не зависел от feature-модуля.
  connections: Array<{ id: number; provider: string; name: string; status: string }>;
};

export type Product = {
  id: number;
  code: string;
  name: string;
  status: ProductStatus;
  siteUrl: string;
  channels: ProductChannelRef[];
  createdAt: string;
  updatedAt: string;
};

export type RouteKey = "administrationOrganization" | "administrationSubscription" | "administrationAudit" | "command" | "employeeDetail" | "employees" | "profile" | "settings" | "salesClientDetail" | "salesClients" | "salesDialogs" | "supportOverview" | "supportDialogs" | "supportPortals" | "supportPortalDetail" | "agents" | "agentDetail" | "aiKnowledge" | "aiKnowledgeCreate" | "aiKnowledgeDetail" | "aiUsage" | "integrations";

export type AppData = {
  employees: Employee[];
  groups: EmployeeGroup[];
  products: Product[];
  agents: AgentCard[];
};

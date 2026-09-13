import type { AgentRef } from "./features/agents/model";

// Роли SPEC-CHATBALLS-0031 §3: OWNER и ADMIN идентичны (владельца нельзя удалить),
// EMPLOYEE работает только в чате; видимость диалогов — по группам (ADR-CHATBALLS-0043).
export type Role = "OWNER" | "ADMIN" | "EMPLOYEE";
export type DeliveryMode = "CLOUD" | "SELF_HOSTED";

export type EmployeeGroupRef = {
  id: number;
  name: string;
};

export type EmployeeGroup = EmployeeGroupRef & {
  color: string;
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
  // «в организации с …» в шапке «Профиля» (дизайн-базлайн v2, кадр P1).
  joinedAt: string;
};

export type AuthenticatedUser = {
  id: number;
  email: string;
  fullName: string;
  avatarUrl?: string | null;
  mustChangePassword: boolean;
  totpEnabled: boolean;
  // Когда последний раз принимался код аутентификатора (кадр P1).
  totpLastUsedAt: string | null;
  deliveryMode: DeliveryMode;
  // Администратор установки: разделы «Платформа» и «Хранилище файлов» — его,
  // это свойства инсталляции, а не организации.
  isInstanceAdmin: boolean;
  memberships: OrganizationMembership[];
  uiTheme: "LIGHT" | "DARK" | "SYSTEM";
  uiAccent: string;
  // Личный выбор языка: пустая строка — «как в организации».
  uiLanguage: string;
  // Язык, на котором сервер отвечает этому человеку прямо сейчас: уже
  // разрешён по цепочке профиль → организация → установка.
  language: string;
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
// источник истины (SPEC-CHATBALLS-0031 §3); фронтенд скрывает недоступное.
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
  avatarUrl?: string | null;
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
  // «Последняя смена» пароля в карточке сотрудника (кадр E3).
  passwordChangedAt?: string | null;
  auditEvents?: EmployeeAuditEvent[];
};

// Ожидающее приглашение существующей учётной записи (статус «Приглашён»):
// роль, должность и группы уже известны и придут вместе с членством.
export type EmployeeInvitation = {
  id: number;
  email: string;
  fullName: string;
  avatarUrl?: string | null;
  role: Role;
  positionTitle: string;
  phone: string;
  groups: EmployeeGroupRef[];
  invitedAt: string;
  expiresAt: string;
};

export type EmployeeAuditEvent = {
  action: string;
  result: string;
  createdAt: string;
};

export type RouteKey = "administrationAudit" | "employeeDetail" | "employees" | "profile" | "settings" | "salesClientDetail" | "salesClients" | "chat" | "supportPortals" | "supportPortalDetail" | "supportPortalSettings" | "agents" | "agentDetail" | "knowledge" | "knowledgeDetail" | "knowledgeCreate" | "knowledgeEdit" | "knowledgeCategories" | "knowledgeImport" | "aiUsage" | "organizationCreate";

export type AppData = {
  groups: EmployeeGroup[];
  agents: AgentRef[];
};

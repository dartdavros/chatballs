export type ChannelPolicy = {
  requiresAuthenticatedProductIdentity: boolean;
  allowAnonymousSessions: boolean;
  allowSelfReportedContact: boolean;
  allowSalesAttribution: boolean;
  allowCheckoutActions: boolean;
};

export type PolicyFlag = keyof ChannelPolicy;

export type PolicyPreset = "SALES" | "SUPPORT" | "CUSTOM";

/** Сводка агента для перехода на его страницу. Конфигурации агента здесь нет. */
export type ChannelAgent = {
  id: number;
  name: string;
  status: string;
  model: string;
};

export type ChannelConnection = {
  id: number;
  provider: string;
  name: string;
  status: string;
};

export type Channel = {
  id: number;
  code: string;
  name: string;
  isActive: boolean;
  product: { id: number; code: string; name: string } | null;
  departmentId: number | null;
  department: string | null;
  departmentName: string | null;
  agent: ChannelAgent | null;
  connections: ChannelConnection[];
  policy: ChannelPolicy;
  counters: { openConversations: number; connections: number };
  createdAt: string;
  updatedAt: string;
};

export type DeletionBlocker = { type: string; count: number };

export type PolicyViolation = { rule: string; field: string; detail: string };

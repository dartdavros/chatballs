// Ответы API сервисов (backend: integrations/service_connections/payloads.py).
// Поля, тексты и готовые сценарии описывает адаптер — экран их не знает заранее.

export type ServiceField = {
  name: string;
  type: string;
  title: string;
  hint: string;
  placeholder: string;
  required: boolean;
  nullable: boolean;
  open?: boolean;
  secret: boolean;
  control: string;
  pattern?: string;
  patternError?: string;
  options?: Array<{ value: string | number | boolean; label: string }>;
  lookup?: string;
  fields?: ServiceField[];
  items?: ServiceField;
};

export type ServiceAuthMethod = {
  key: string;
  title: string;
  about: string;
  note: string;
  accessLabel: string;
  savedLabel: string;
  oauth: boolean;
  checkable: boolean;
  checkNote: string;
  checkInputs: ServiceField[] | null;
  fields: ServiceField[];
};

export type ServicePreset = {
  key: string;
  version: number;
  title: string;
  purpose: string;
  requiredConnections: string[];
  requiredPermissions: string[];
  parameters: ServiceField[];
  steps: Array<{ id: string; title: string; target: string }>;
};

export type ServiceHelp = { title: string; steps: string[]; paragraphs: string[]; link: string; url: string };

export type ServiceAdapter = {
  key: string;
  version: number;
  title: string;
  about: string;
  connectLead: string;
  hostLabel: string;
  logo: { light: string; dark: string };
  help: ServiceHelp | null;
  authMethods: ServiceAuthMethod[];
  settings: ServiceField[];
  presets: ServicePreset[];
  operations: Array<{ key: string; title: string; input: ServiceField; output: ServiceField; entityKind?: string }>;
  entities?: Array<{ key: string; title: string; fields: ServiceField; nativeEntities: string[];
    synchronization?: { directions: Array<"forward" | "reverse" | "both">; deletion: Array<"unlink" | "keep" | "propagate"> } }>;
  events: Array<{ key: string; title: string; payload: ServiceField }>;
};

export type ServiceError = { code: string; title: string; text: string };

export type ServiceStatus = "ok" | "lost" | "unchecked";

export type ServiceConnection = {
  id: number;
  name: string;
  adapter: string;
  authMethod: string;
  status: ServiceStatus;
  isActive: boolean;
  host: string;
  hasCredentials: boolean;
  incompatible: boolean;
  lastCheckedAt: string | null;
  error: ServiceError | null;
  scenarios: { enabled: number };
  createdAt: string;
};

export type OAuthState = {
  id: string;
  status: "pending" | "completed" | "denied" | "failed";
  connectionId: number | null;
  error: ServiceError | null;
};

/** Отказ запроса: ошибки полей формы или понятная причина проверки доступа. */
export type ServiceFailure = { fields: Record<string, string>; error: ServiceError | null; message: string };

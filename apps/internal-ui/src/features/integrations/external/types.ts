import type { HttpMethod } from "./httpMethods";

export type ServerKind = "mcp" | "http";
export type ParameterSource = { type: "ai" } | { type: "contact"; field: "name" | "email" | "phone" }
  | { type: "web_field"; integrationId: number; key: string };
export type ToolParameter = {
  name: string;
  type: "string" | "number" | "boolean";
  required: boolean;
  location: "path" | "query" | "body";
  description: string;
  source: ParameterSource;
};
export type ServerHeader = { name: string; value: string; secret: boolean; saved?: boolean };
export type McpTool = {
  name: string;
  title: string;
  description: string;
  inputSchema: Record<string, unknown>;
  readOnlyHint: boolean;
  readOnlyConfirmation: { confirmedBy: { id: number; name: string } | null; confirmedAt: string } | null;
};
export type ExternalServer = {
  type: ServerKind;
  url: string;
  description: string;
  headers: ServerHeader[];
  toolName?: string;
  method?: HttpMethod;
  readOnly?: boolean;
  parameters?: ToolParameter[];
  tools?: McpTool[];
  toolsRefreshedAt?: string | null;
  toolsState?: "not_loaded" | "loaded" | "no_tools" | "unreachable" | "unauthorized" | "address_forbidden";
};
export type ServerDraft = {
  name: string;
  isActive: boolean;
  externalServer: ExternalServer;
};
export type FieldErrors = Record<string, string[]>;

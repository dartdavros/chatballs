export interface HealthResponse {
  status: "ok" | "degraded";
  service?: string;
  checks?: Record<string, boolean>;
}

export type { MessagePresentation } from "./messagePresentation";
export type { SiteEventField, PublicSiteEventRule, SiteEventRule, SiteEvent, SiteEventState, SiteEventData } from "./siteEvents";
export type { MicrophoneMode, WebSpeechCapabilities, SpeechCapabilities } from "./speech";

export interface SiteField {
  key: string;
  label: string;
  type: "string" | "number" | "boolean" | "datetime" | "enum" | "email" | "phone" | "url";
  value: string | number | boolean;
  display: string;
  color?: string;
  updatedAt: string;
}

export interface DepartmentSummary {
  departmentId: string;
  generatedAt: string;
  attentionStatus: "NORMAL" | "ATTENTION" | "CRITICAL";
  summaryText: string;
  workspaceRoute: string;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  service?: string;
  checks?: Record<string, boolean>;
}

export interface DepartmentSummary {
  departmentId: string;
  generatedAt: string;
  attentionStatus: "NORMAL" | "ATTENTION" | "CRITICAL";
  summaryText: string;
  workspaceRoute: string;
}

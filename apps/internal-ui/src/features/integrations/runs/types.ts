import type { ServiceField } from "../services/types";

export type RunState = "queued" | "running" | "reconciling" | "approval" | "pending" | "completed" | "failed" | "unknown" | "cancelled" | "decision";
export type RunSummary = {
  ai?: boolean;
  id: string; number: number; name: string; connection: string; state: RunState; stateLabel: string;
  initiator: string; conversationId: number | null; createdAt: string; finishedAt: string | null;
  cancelRequested: boolean; dataCleared: boolean; revision: number; definitionUpdatedAt: string | null;
  progress: Array<{ title: string; state: RunState; stateLabel: string }>;
};
export type RunStep = {
  fileNames?: Record<string, string>;
  editToken?: string; editing?: boolean; connectionId?: number;
  path: string; title: string; state: RunState; stateLabel: string; attempt: number; error: string;
  inputSchema: ServiceField | null; outputSchema: ServiceField | null; arguments: unknown; result: unknown; approvalDigest?: string;
  depth?: number; deadline?: string; prompt?: string; scope?: Array<{ kind: "iteration" | "branch"; number: number }>; decision?: { generation: string; digest: string };
};
export type RunConflict = { digest: string; leftTitle: string; rightTitle: string; items: Array<{
  id: string; field: string; left: unknown; right: unknown; leftAt: string | null; rightAt: string | null;
  leftSchema: ServiceField | null; rightSchema: ServiceField | null;
}> };
export type RunDetail = RunSummary & { files?: Array<{ id: string; name: string }>; controls: string[]; steps: RunStep[]; reconcilePath?: string; conflict?: RunConflict | null; journal: Array<{ id: number; label: string; createdAt: string }> };
export type RunPage = { items: RunSummary[]; count: number; page: number; pageSize: number;
  filters: { connections: Array<{ id: number; name: string }>; initiators: Array<{ initiator_id: number; initiator__user__full_name: string }> } };
export type ManualActionPresentation = {
  source: { key: string; title: string; subtitle?: string; kind: "service" | "scenarios" | "native" };
  categoryPath: Array<{ key: string; title: string }>;
};
export type ManualAction = { id: string; kind: "scenario" | "operation"; title: string; parameters: ServiceField;
  presentation?: ManualActionPresentation;
  initialValues?: Record<string, unknown>;
  plan?: string[];
  connectionId?: number | "chatballs"; operationKey?: string; connection?: string; readOnly?: boolean; available?: boolean; reason?: string };
export type RetentionPolicy = { stepDays: number; journalDays: number; version: number; effectiveAt: string | null };
export type ManualCatalog = { items: ManualAction[]; files: Array<{ id: string; name: string }> };
export type ManualActionSummary = Omit<ManualAction, "parameters" | "initialValues" | "plan" | "available" | "presentation"> & {
  available: boolean; presentation: ManualActionPresentation;
};
export type ManualActionCatalog = { items: ManualActionSummary[]; files: ManualCatalog["files"] };
export type ManualActionDetail = { item: ManualAction; files: ManualCatalog["files"] };
export type PlanPreview = { confirmation: string; operation: string; inputSchema: ServiceField; arguments: unknown; note: string };

import type { ServiceAdapter, ServiceConnection, ServiceField } from "../services/types";

export type DataKind = "string" | "integer" | "number" | "boolean" | "date" | "datetime" | "object" | "array" | "enum" | "lookup" | "file" | "json";
export type DataSchema = {
  type: DataKind; title?: string; required?: boolean; nullable?: boolean; open?: boolean;
  properties?: Record<string, DataSchema>; items?: DataSchema; options?: Array<string | number | boolean>; lookup?: string;
};
export type BindingSource = "constant" | "input" | "parameter" | "context" | "event" | "step" | "item" | "error";
export type Binding = {
  source: BindingSource; value?: unknown; name?: string; path?: string; step?: string; transform?: string; args?: Record<string, unknown>; aspect?: "state";
};
export type BoundValue = Binding | BoundValue[] | { [key: string]: BoundValue };
export type Condition = { left?: Binding; op?: string; right?: Binding; kind?: "context_present" | "no_link" | "has_link" | "tag" | "channel";
  path?: string; entity?: string; connection?: string | number; tag?: number; scope?: "contact" | "conversation"; present?: boolean };
export type Conditions = { mode: "all" | "any"; items: Condition[] };
export type BlockKind = "action" | "if" | "foreach" | "parallel" | "call" | "wait" | "try";
export type Block = {
  id: string; kind: BlockKind; name?: string; target?: string; connection?: string; inputs?: Record<string, BoundValue>;
  condition?: Conditions; then?: Block[]; else?: Block[]; body?: Block[]; catch?: Block[]; branches?: Block[][];
  list?: Binding; concurrency?: number; onError?: "stop" | "continue" | "wait"; after?: "continue" | "fail";
  scenario?: string; mode?: "duration" | "until" | "event" | "confirmation" | "reply" | "clock";
  duration?: number; until?: Binding; event?: string; timeout?: number; onTimeout?: "continue" | "end";
  day?: "next" | "work" | "date"; date?: string; time?: string; timezone?: string; approver?: string; message?: string;
};
export type TriggerKind = "staff" | "ai" | "chatballs" | "service" | "schedule" | "api" | "scenario";
export type Trigger = {
  id: string; kind: TriggerKind; event?: string; connection?: string; agents?: number[];
  timezone?: string; days?: number[]; date?: string; time?: string; misfire?: "once" | "skip";
  ambiguous?: "first" | "second"; nonexistent?: "skip" | "next";
  frequency?: "daily" | "weekdays" | "days" | "monthly"; dayOfMonth?: number | "last";
};
export type Access = {
  staff: number[]; groups: number[]; aiMode: "off" | "confirm" | "autonomous"; delegated: boolean;
  scope: "conversation" | "contact" | "organization"; confirm: "effects" | "always";
};
export type Mapping = { left: string; right: string; direction: "forward" | "reverse"; values?: Array<{ from: unknown; to: unknown }>; transform?: string; args?: Record<string, unknown> };
export type SyncPair = {
  id: string; enabled: boolean; left: { connection: string; entity: string }; right: { connection: string; entity: string };
  direction: "forward" | "reverse" | "both"; fields: Mapping[]; sourceOfTruth: "left" | "right" | "latest";
  conflict: "source" | "latest" | "manual"; deletion: "unlink" | "keep" | "propagate";
  causality: { suppressEcho: true; requireExplicitLink: true };
};
export type ScenarioDocument = {
  version: 1; parameters: DataSchema; results: DataSchema; outputs: Record<string, BoundValue>;
  triggers: Trigger[]; conditions: Conditions; steps: Block[]; access: Access; synchronization: SyncPair[];
};
export type Issue = { path: string; code: string; message: string };
export type Scenario = {
  categoryPath?: string[];
  agentPolicies?: Array<{ agent: number; mode: "off" | "self" | "ask"; revision: number }>;
  automationError?: string;
  id: string; name: string; revision: number; enabled: boolean; definition: ScenarioDocument; issues?: Issue[];
  origin: { adapter: string; key: string; version: number | null }; connections: number[]; updatedAt: string;
  triggers?: TriggerKind[];
  nativeEvents?: string[];
  accessScope?: Access["scope"];
  externalKeys?: ExternalKey[];
};
export type ExternalKey = { id: string; trigger: string; url: string; key?: string };
export type ExchangeSettings = { revision: number; definition: { version: 1; synchronization: SyncPair[] };
  result?: { stateLabel: string; finishedAt: string | null } | null; error?: string };
export type Entity = { key: string; title: string; fields: ServiceField; writableFields?: string[]; nativeEntities?: string[];
  synchronization?: { directions: SyncPair["direction"][]; deletion: SyncPair["deletion"][] } };
export type Operation = { key: string; title: string; input: ServiceField; output: ServiceField; entityKind?: string };
export type EditorCatalog = {
  transforms: Array<{ key: string; title: string; inputTypes: string[]; outputType: string; arguments: ServiceField }>;
  timezone: string; groups: Array<{ id: number; name: string }>; staff: Array<{ id: number; name: string }>;
  agents: Array<{ id: number; name: string }>; files: Array<{ id: string; name: string }>;
  labels: Array<{ id: number; name: string }>; channels: Array<{ id: number; name: string }>;
  events: Array<{ key: string; title: string; payload: ServiceField }>;
  context: ServiceField; nativeActions: Operation[];
  entities: Entity[];
  scenarios: Array<{ id: string; name: string; parameters: DataSchema; results: DataSchema }>;
  adapters: ServiceAdapter[]; connections: ServiceConnection[];
};
export type BlockLocation = { parent: string | null; branch: string };
export type Drawer = { kind: "block"; id: string } | { kind: "add"; location: BlockLocation }
  | { kind: "trigger"; id: string } | { kind: "addTrigger" } | { kind: "condition"; index: number }
  | { kind: "access" } | { kind: "parameters" } | { kind: "synchronization" };

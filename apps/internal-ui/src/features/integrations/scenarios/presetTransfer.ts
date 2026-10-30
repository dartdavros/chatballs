import type { ExternalKey, Scenario } from "./types";

// One navigation handoff; secrets never enter the URL or browser storage.
let pending: { id: string; keys: ExternalKey[] } | undefined;
export function retainPresetKeys(scenario: Scenario) {
  const keys = scenario.externalKeys?.filter(key => key.key);
  pending = keys?.length ? { id: scenario.id, keys } : undefined;
}
export function takePresetKeys(id: string) {
  const keys = pending?.id === id ? pending.keys : undefined;
  pending = undefined;
  return keys;
}

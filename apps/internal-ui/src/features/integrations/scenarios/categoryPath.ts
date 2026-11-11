import type { Scenario } from "./types";

export const CATEGORY_DEPTH = 3;
export const CATEGORY_NAME_LENGTH = 80;

export function parseCategoryPath(value: string): string[] {
  return value.trim() ? value.split("/").map(part => part.trim()) : [];
}

export function validCategoryPath(path: string[]): boolean {
  return path.length <= CATEGORY_DEPTH && path.every(part => Boolean(part.trim())
    && Array.from(part.trim()).length <= CATEGORY_NAME_LENGTH && !/[\u0000-\u001f\u007f/]/.test(part));
}

export function scenarioSnapshot(scenario: Scenario): string {
  return JSON.stringify({ name: scenario.name, definition: scenario.definition,
    enabled: scenario.enabled, agentPolicies: scenario.agentPolicies, categoryPath: scenario.categoryPath ?? [] });
}

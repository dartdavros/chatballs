import { blockPath, blockTitle, operationFor, childLists } from "./model";
import type { Block, EditorCatalog, Issue, ScenarioDocument } from "./types";

export function presentIssue(issue: Issue, document: ScenarioDocument, catalog: EditorCatalog) {
  const steps = (items: Block[]): Block[] => items.flatMap(step => [step, ...childLists(step).flatMap(([, list]) => steps(list))]);
  const block = steps(document.steps).find(step => issue.path.startsWith(`${blockPath(document.steps, step.id)}.inputs.`));
  if (!block) return { message: issue.message };
  const names = issue.path.slice(`${blockPath(document.steps, block.id)}.inputs.`.length).split(".");
  let schema = operationFor(catalog, block)?.input;
  let label = "";
  for (const name of names) {
    if (name === "$") continue;
    schema = schema?.type === "array" ? schema.items : schema?.fields?.find(field => field.name === name);
    if (schema?.title) label = schema.title;
  }
  return { block: block.id, message: [blockTitle(block, catalog), label, issue.message].filter(Boolean).join(" · ") };
}

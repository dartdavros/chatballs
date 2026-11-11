import { language, t } from "../../../i18n";
import type { ManualAction, ManualActionSummary, ManualActionPresentation } from "./types";

export type ActionPickerGroup = {
  key: string; title: string; subtitle?: string; sourceKind?: ManualActionPresentation["source"]["kind"];
  groups: ActionPickerGroup[]; actions: ManualActionSummary[]; count: number;
};

export const actionKey = (action: Pick<ManualAction, "id" | "kind">) => `${action.kind}:${action.id}`;
export const normalizeActionSearch = (value: string) => value.toLocaleLowerCase().replaceAll("ё", "е").trim();
export const actionSearchWords = (search: string) => normalizeActionSearch(search).split(/\s+/).filter(Boolean);

export function actionCaption(action: ManualActionSummary) {
  return [t(action.kind === "scenario" ? "runs.scenario" : "run_action_picker.operation"),
    action.presentation.source.subtitle || action.connection,
    action.readOnly ? t("runs.read_only") : ""].filter(Boolean).join(" · ");
}

export function actionPresentationPath(action: ManualAction) {
  const presentation = action.presentation;
  if (!presentation) return action.connection ?? "";
  return [[presentation.source.title, presentation.source.subtitle].filter(Boolean).join(" · "),
    ...presentation.categoryPath.map(category => category.title)].join(" / ");
}

export function buildActionPickerGroups(actions: readonly ManualActionSummary[], search = ""): ActionPickerGroup[] {
  const roots: ActionPickerGroup[] = [];
  const groups = new Map<string, ActionPickerGroup>();
  const words = actionSearchWords(search);
  const seen = new Set<string>();
  for (const action of actions) {
    if (action.available !== true || seen.has(actionKey(action))) continue;
    seen.add(actionKey(action));
    const { source, categoryPath } = action.presentation;
    const text = normalizeActionSearch([action.title, actionCaption(action), source.title, source.subtitle ?? "",
      ...categoryPath.map(category => category.title)].join(" "));
    if (!words.every(word => text.includes(word))) continue;
    const parts: Array<{ key: string; title: string; subtitle?: string; sourceKind?: ActionPickerGroup["sourceKind"] }> = [
      { ...source, sourceKind: source.kind }, ...categoryPath,
    ];
    let siblings = roots;
    let group: ActionPickerGroup | undefined;
    const path: string[] = [];
    for (const part of parts) {
      path.push(part.key);
      const key = JSON.stringify(path);
      group = groups.get(key);
      if (!group) {
        group = { ...part, key, groups: [], actions: [], count: 0 };
        groups.set(key, group);
        siblings.push(group);
      }
      group.count++;
      siblings = group.groups;
    }
    group?.actions.push(action);
  }
  const compare = (left: string, right: string) => left.localeCompare(right, language(), { sensitivity: "base", numeric: true });
  const order = { service: 0, scenarios: 1, native: 2 };
  roots.sort((left, right) => order[left.sourceKind ?? "native"] - order[right.sourceKind ?? "native"]
    || compare(left.title, right.title) || compare(left.subtitle ?? "", right.subtitle ?? "") || compare(left.key, right.key));
  const sortActions = (group: ActionPickerGroup) => {
    group.actions.sort((left, right) => compare(left.title, right.title) || compare(actionKey(left), actionKey(right)));
    group.groups.forEach(sortActions);
  };
  roots.forEach(sortActions);
  return roots;
}

/** Search expands matching paths without changing the user's normal expansion. */
export function isActionGroupOpen(key: string, search: string, expanded: ReadonlySet<string>, collapsedSearch: ReadonlySet<string>) {
  return actionSearchWords(search).length > 0 ? !collapsedSearch.has(key) : expanded.has(key);
}

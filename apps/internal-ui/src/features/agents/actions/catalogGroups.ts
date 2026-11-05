import { t } from "../../../i18n";
import type { AgentAction } from "./model";

// Namespaces are part of the native registry contract, not translated titles
// or a second list of operations. New operations inherit their domain group.
const domains = {
  conversations: "conversations", messages: "conversations", comments: "conversations",
  participants: "conversations", transfers: "conversations", labels: "conversations",
  ratings: "conversations", quality: "conversations",
  contacts: "contacts", employees: "employees", groups: "employees", availability: "employees",
  agents: "agents", skills: "agents", knowledge: "knowledge", portals: "portals",
  files: "files", calls: "calls", notifications: "notifications", reports: "reports",
  settings: "settings", organizations: "settings", rules: "settings", templates: "templates",
  connections: "integrations", services: "integrations", entity_links: "integrations",
  synchronization: "integrations", webchat: "integrations",
  scenarios: "scenario_management", runs: "scenario_management",
} as const;
type Domain = typeof domains[keyof typeof domains];
export type ActionGroup = { key: string; title: string; rows: AgentAction[] };

export function actionCategory(row: AgentAction): Pick<ActionGroup, "key" | "title"> {
  const [kind, target] = row.id.split(":");
  if (kind === "scenario") return { key: "scenarios", title: t("agent_actions.category_scenarios") };
  if (kind === "operation") return { key: `connection:${target}`, title: row.subtitle };
  const namespace = target?.split(".")[0];
  const domain: Domain | "other" = domains[namespace as keyof typeof domains] ?? "other";
  return { key: `native:${domain}`, title: t(`agent_actions.category_${domain}`) };
}

export function groupActions(rows: readonly AgentAction[], search = ""): ActionGroup[] {
  const groups = new Map<string, ActionGroup>();
  const query = search.trim().toLocaleLowerCase();
  for (const row of rows) {
    const category = actionCategory(row);
    if (query && ![row.title, category.title, row.subtitle].some(text => text.toLocaleLowerCase().includes(query))) continue;
    let group = groups.get(category.key);
    if (!group) { group = { ...category, rows: [] }; groups.set(group.key, group); }
    group.rows.push(row);
  }
  return [...groups.values()];
}

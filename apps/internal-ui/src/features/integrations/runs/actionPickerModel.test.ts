import { beforeEach, describe, expect, it } from "vitest";
import { setCurrentLanguage } from "@chatballs/shared";
import { actionKey, buildActionPickerGroups, isActionGroupOpen, type ActionPickerGroup } from "./actionPickerModel";
import type { ManualActionSummary } from "./types";

const operation = (connectionId: number, title = "Добавить лида", category = "crm"): ManualActionSummary => ({
  id: `${connectionId}:lead.create`, kind: "operation", title, connectionId, available: true,
  presentation: { source: { key: `service:${connectionId}`, title: "Битрикс24", subtitle: connectionId === 1 ? "Отдел продаж" : "Интернет-магазин", kind: "service" },
    categoryPath: [{ key: category, title: category === "crm" ? "CRM" : "Пользователи" }] },
});
const flatten = (groups: ActionPickerGroup[]): ManualActionSummary[] => groups.flatMap(group => [...flatten(group.groups), ...group.actions]);
beforeEach(() => setCurrentLanguage("ru"));

describe("conversation action catalog", () => {
  it("keeps identically named services, categories and actions in their connection", () => {
    const first = operation(1);
    const second = operation(2);
    const groups = buildActionPickerGroups([first, second]);
    expect(groups).toHaveLength(2);
    expect(groups.map(group => group.subtitle)).toEqual(["Интернет-магазин", "Отдел продаж"]);
    expect(groups[0].groups[0].key).not.toBe(groups[1].groups[0].key);
    expect(flatten(groups).map(actionKey)).toEqual(["operation:2:lead.create", "operation:1:lead.create"]);
  });

  it("matches each word across action, source, category and connection without case or ё differences", () => {
    const lead = operation(1, "Добавить обращение");
    const shop = operation(2, "Обновить счёт");
    expect(flatten(buildActionPickerGroups([lead, shop], "БИТРИКС crm магазин счет"))).toEqual([shop]);
    expect(flatten(buildActionPickerGroups([lead, shop], "продаж обращение"))).toEqual([lead]);
    expect(buildActionPickerGroups([lead, shop], "неизвестное")).toEqual([]);
  });

  it("searches descendants through group titles and prunes empty branches with exact counts", () => {
    const crm = operation(1);
    const user = { ...operation(1, "Найти пользователя", "users"), id: "1:user.list" };
    const groups = buildActionPickerGroups([crm, user, operation(2)], "crm");
    expect(groups.map(group => group.count)).toEqual([1, 1]);
    expect(groups[0].groups.map(group => group.title)).toEqual(["CRM"]);
    expect(flatten(buildActionPickerGroups([crm, user], "битрикс24"))).toEqual([crm, user]);
  });

  it("excludes unavailable and unspecified availability from search, counts and groups", () => {
    const denied = { ...operation(1), available: false };
    const missing = { ...operation(2), available: undefined } as unknown as ManualActionSummary;
    expect(buildActionPickerGroups([denied, missing])).toEqual([]);
    expect(buildActionPickerGroups([denied, operation(2)], "продаж")).toEqual([]);
  });

  it("honors arbitrary scenario paths and supports uncategorized operations without invented groups", () => {
    const scenario: ManualActionSummary = { id: "42", kind: "scenario", title: "Возврат", available: true,
      presentation: { source: { key: "scenarios", title: "Сценарии", kind: "scenarios" },
        categoryPath: [{ key: "sales", title: "Продажи" }, { key: "refunds", title: "Возвраты" }] } };
    const direct = { ...operation(1), presentation: { ...operation(1).presentation, categoryPath: [] } };
    const groups = buildActionPickerGroups([scenario, direct]);
    expect(groups[1].groups[0].groups[0].actions).toEqual([scenario]);
    expect(groups[0].groups).toEqual([]);
    expect(groups[0].actions).toEqual([direct]);
  });

  it("does not count duplicate identities twice and keeps scenario/operation identities separate", () => {
    const action = operation(1);
    const scenario = { ...action, kind: "scenario" as const };
    const groups = buildActionPickerGroups([action, action, scenario]);
    expect(groups[0].count).toBe(2);
    expect(flatten(groups)).toEqual([action, scenario]);
  });

  it("search expansion and manual collapse leave the normal expansion intact", () => {
    const expanded = new Set(["service"]);
    const collapsedSearch = new Set(["category"]);
    expect(isActionGroupOpen("category", "лид", expanded, new Set())).toBe(true);
    expect(isActionGroupOpen("category", "лид", expanded, collapsedSearch)).toBe(false);
    expect(isActionGroupOpen("service", "", expanded, collapsedSearch)).toBe(true);
    expect(isActionGroupOpen("category", "   ", expanded, collapsedSearch)).toBe(false);
    expect([...expanded]).toEqual(["service"]);
  });

  it("filters hundreds of actions without losing matches or accumulating hidden counts", () => {
    const actions = Array.from({ length: 600 }, (_, index) => ({ ...operation(index % 2 + 1, `Действие ${index}`), id: `${index}` }));
    const groups = buildActionPickerGroups(actions, "магазин действие 599");
    expect(flatten(groups).map(action => action.id)).toEqual(["599"]);
    expect(groups[0].count).toBe(1);
  });

  it("orders services before scenarios and native actions independently of the API order", () => {
    const service = operation(1);
    const scenario: ManualActionSummary = { ...operation(2), id: "scenario", kind: "scenario",
      presentation: { source: { key: "scenarios", kind: "scenarios", title: "Сценарии" }, categoryPath: [] } };
    const native: ManualActionSummary = { ...operation(3), id: "chatballs:contacts.get",
      presentation: { source: { key: "native", kind: "native", title: "Chatballs" }, categoryPath: [] } };
    expect(buildActionPickerGroups([native, scenario, service]).map(group => group.sourceKind)).toEqual(["service", "scenarios", "native"]);
    const before = buildActionPickerGroups([service])[0].key;
    expect(buildActionPickerGroups([{ ...service, presentation: { ...service.presentation, source: { ...service.presentation.source, title: "Перевод" } } }])[0].key).toBe(before);
  });
});

import { setCurrentLanguage } from "@chatballs/shared";
import { beforeEach, describe, expect, it } from "vitest";
import { actionCategory, groupActions } from "./catalogGroups";
import { changedActions, type AgentAction } from "./model";

const row = (id: string, title = "Действие", subtitle = "Chatballs"): AgentAction => ({
  id, title, subtitle, mode: "off", revision: 7, available: true, writes: true,
});
beforeEach(() => setCurrentLanguage("ru"));

describe("каталог прав агента", () => {
  it("даёт каждой строке ровно одну предметную категорию, включая будущие операции", () => {
    const ids = ["native:contacts.card.get", "native:agents.get", "native:comments.post", "native:knowledge.get", "native:portals.get"];
    const rows = ids.map(id => row(id));
    const grouped = groupActions(rows);
    expect(grouped.flatMap(group => group.rows).map(item => item.id).sort()).toEqual(ids.sort());
    expect(grouped.some(group => group.key === "native:other")).toBe(false);
    expect(actionCategory(row("native:agents.future.post")).key).toBe("native:agents");
    expect(groupActions([row("native:future.operation")])[0].rows).toHaveLength(1);
  });

  it("выделяет сценарии и подключения по устойчивым ID даже при одинаковых названиях", () => {
    const rows = [row("native:scenarios.get"), row("scenario:123"),
      row("operation:1:a", "Создать", "CRM"), row("operation:1:b", "Найти", "CRM"), row("operation:2:a", "Создать", "CRM")];
    expect(groupActions(rows).map(group => [group.key, group.rows.length])).toEqual([
      ["native:scenario_management", 1], ["scenarios", 1], ["connection:1", 2], ["connection:2", 1],
    ]);
    const translated = { ...rows[0], title: "Translation", subtitle: "Другой перевод" };
    expect(actionCategory(translated).key).toBe(actionCategory(rows[0]).key);
  });

  it("ищет без регистра по названию, категории и подключению, убирая пустые группы", () => {
    const rows = [row("native:contacts.card.get", "Получить контакт"), row("native:agents.get", "Список"),
      row("operation:1:a", "Найти", "Мой CRM"), row("scenario:one", "Возврат")];
    expect(groupActions(rows, " пОЛУчить ").flatMap(group => group.rows)).toEqual([rows[0]]);
    expect(groupActions(rows, "АГЕНТЫ").flatMap(group => group.rows)).toEqual([rows[1]]);
    expect(groupActions(rows, "мой crm").flatMap(group => group.rows)).toEqual([rows[2]]);
    expect(groupActions(rows, "сценарии").flatMap(group => group.rows)).toEqual([rows[3]]);
    expect(groupActions(rows, "несуществующее")).toEqual([]);
    expect(groupActions(rows, " ").flatMap(group => group.rows)).toEqual(rows);
    expect(groupActions([])).toEqual([]);
  });

  it("сохраняет все изменённые режимы вместе с ревизиями, включая скрытые поиском", () => {
    const saved = [row("native:contacts.card.get", "Контакт"), row("native:agents.get", "Агент")];
    const draft = saved.map((item, index) => ({ ...item, mode: index === 0 ? "self" as const : "ask" as const }));
    expect(groupActions(draft, "Агент").flatMap(group => group.rows)).toEqual([draft[1]]);
    expect(groupActions(draft, "Контакт").flatMap(group => group.rows)).toEqual([draft[0]]);
    expect(changedActions(draft, saved)).toEqual(draft);
    expect(changedActions(draft, saved).map(({ id, mode, revision }) => ({ id, mode, revision }))).toEqual([
      { id: saved[0].id, mode: "self", revision: 7 }, { id: saved[1].id, mode: "ask", revision: 7 },
    ]);
    expect(changedActions(saved, saved)).toEqual([]);
    expect(changedActions(draft, draft)).toEqual([]);
    expect(saved.every(item => item.mode === "off")).toBe(true);
  });
});

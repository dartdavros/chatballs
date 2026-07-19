import { describe, expect, it } from "vitest";

import {
  emptyKnowledgeEditorState,
  knowledgeEditorError,
  knowledgeEditorRequest,
  knowledgeEditorState,
} from "./knowledgeEditorModel";
import type { KnowledgeItem } from "./types";

describe("knowledge editor model", () => {
  it("requires title, category and at least one department for department scope", () => {
    const empty = emptyKnowledgeEditorState();
    expect(knowledgeEditorError(empty)).toBe("Укажите заголовок знания");
    expect(knowledgeEditorError({ ...empty, title: "Правила" })).toBe("Выберите категорию");
    expect(knowledgeEditorError({ ...empty, title: "Правила", categoryId: 4, visibility: "DEPARTMENTS" })).toBe("Выберите хотя бы один отдел");
    expect(knowledgeEditorError({ ...empty, title: "Правила", categoryId: 4, visibility: "DEPARTMENTS", departmentIds: [2] })).toBeNull();
  });

  it("never sends departments for organization visibility", () => {
    const request = knowledgeEditorRequest({
      ...emptyKnowledgeEditorState(4),
      title: " Правила ",
      description: " Описание ",
      visibility: "ORGANIZATION",
      departmentIds: [2, 3],
    });
    expect(request).toMatchObject({
      title: "Правила",
      description: "Описание",
      categoryId: 4,
      visibility: "ORGANIZATION",
      departmentIds: [],
    });
  });

  it("hydrates all editable scope fields from a knowledge item", () => {
    const item = {
      id: 7,
      title: "Правила",
      description: "Описание",
      content: "Markdown",
      category: { id: 4, name: "Скрипты", parentId: 1 },
      visibility: "DEPARTMENTS",
      departments: [{ id: 2, code: "sales", name: "Продажи" }],
      isEnabled: false,
      attachments: [],
      agentsCount: 0,
      fragmentsCount: 2,
      createdAt: "2026-07-01T00:00:00Z",
      updatedAt: "2026-07-02T00:00:00Z",
    } satisfies KnowledgeItem;
    expect(knowledgeEditorState(item)).toMatchObject({ categoryId: 4, departmentIds: [2], visibility: "DEPARTMENTS", isEnabled: false });
  });
});

import { describe, expect, it } from "vitest";

import {
  emptyKnowledgeEditorState,
  knowledgeEditorError,
  knowledgeEditorRequest,
  knowledgeEditorState,
} from "./knowledgeEditorModel";
import type { KnowledgeItem } from "./types";

describe("knowledge editor model", () => {
  it("requires title and category", () => {
    const empty = emptyKnowledgeEditorState();
    expect(knowledgeEditorError(empty)).toBe("Укажите заголовок знания");
    expect(knowledgeEditorError({ ...empty, title: "Правила" })).toBe("Выберите категорию");
    expect(knowledgeEditorError({ ...empty, title: "Правила", categoryId: 4 })).toBeNull();
  });

  it("trims title and description in the request payload", () => {
    const request = knowledgeEditorRequest({
      ...emptyKnowledgeEditorState(4),
      title: " Правила ",
      description: " Описание ",
    });
    expect(request).toMatchObject({
      title: "Правила",
      description: "Описание",
      categoryId: 4,
    });
  });

  it("hydrates all editable fields from a knowledge item", () => {
    const item = {
      id: 7,
      title: "Правила",
      description: "Описание",
      content: "Markdown",
      category: { id: 4, name: "Скрипты", parentId: 1 },
      isEnabled: false,
      attachments: [],
      agentsCount: 0,
      fragmentsCount: 2,
      createdAt: "2026-07-01T00:00:00Z",
      updatedAt: "2026-07-02T00:00:00Z",
    } satisfies KnowledgeItem;
    expect(knowledgeEditorState(item)).toMatchObject({
      categoryId: 4,
      content: "Markdown",
      description: "Описание",
      isEnabled: false,
      title: "Правила",
    });
  });
});

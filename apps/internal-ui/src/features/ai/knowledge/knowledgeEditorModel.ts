import type { KnowledgeCreateRequest, KnowledgeItem, KnowledgeVisibility } from "./types";

export type KnowledgeEditorState = {
  categoryId: number | null;
  content: string;
  departmentIds: number[];
  description: string;
  isEnabled: boolean;
  title: string;
  visibility: KnowledgeVisibility;
};

export function emptyKnowledgeEditorState(categoryId: number | null = null): KnowledgeEditorState {
  return {
    categoryId,
    content: "",
    departmentIds: [],
    description: "",
    isEnabled: true,
    title: "",
    visibility: "ORGANIZATION",
  };
}

export function knowledgeEditorState(item: KnowledgeItem): KnowledgeEditorState {
  return {
    categoryId: item.category.id,
    content: item.content ?? "",
    departmentIds: item.departments.map((department) => department.id),
    description: item.description,
    isEnabled: item.isEnabled,
    title: item.title,
    visibility: item.visibility,
  };
}

export function knowledgeEditorRequest(state: KnowledgeEditorState): KnowledgeCreateRequest {
  return {
    categoryId: state.categoryId ?? undefined,
    content: state.content,
    departmentIds: state.visibility === "DEPARTMENTS" ? state.departmentIds : [],
    description: state.description.trim(),
    isEnabled: state.isEnabled,
    title: state.title.trim(),
    visibility: state.visibility,
  };
}

export function knowledgeEditorError(state: KnowledgeEditorState): string | null {
  if (!state.title.trim()) return "Укажите заголовок знания";
  if (state.categoryId === null) return "Выберите категорию";
  if (state.visibility === "DEPARTMENTS" && state.departmentIds.length === 0) {
    return "Выберите хотя бы один отдел";
  }
  return null;
}

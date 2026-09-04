import type { KnowledgeCreateRequest, KnowledgeItem } from "./types";

export type KnowledgeEditorState = {
  categoryId: number | null;
  content: string;
  description: string;
  isEnabled: boolean;
  title: string;
};

export function emptyKnowledgeEditorState(categoryId: number | null = null): KnowledgeEditorState {
  return {
    categoryId,
    content: "",
    description: "",
    isEnabled: true,
    title: "",
  };
}

export function knowledgeEditorState(item: KnowledgeItem): KnowledgeEditorState {
  return {
    categoryId: item.category.id,
    content: item.content ?? "",
    description: item.description,
    isEnabled: item.isEnabled,
    title: item.title,
  };
}

export function knowledgeEditorRequest(state: KnowledgeEditorState): KnowledgeCreateRequest {
  return {
    categoryId: state.categoryId ?? undefined,
    content: state.content,
    description: state.description.trim(),
    isEnabled: state.isEnabled,
    title: state.title.trim(),
  };
}

export function knowledgeEditorError(state: KnowledgeEditorState): string | null {
  if (!state.title.trim()) return "Укажите заголовок знания";
  if (state.categoryId === null) return "Выберите категорию";
  return null;
}

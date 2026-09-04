import { Icon } from "../../../shared/icons";
import { FormField } from "../../../shared/form-controls";
import type { KnowledgeEditorState } from "./knowledgeEditorModel";
import { knowledgeCategoryPath } from "./knowledgeTree";
import type { KnowledgeCategory } from "./types";

export function KnowledgeEditorFields({
  categories,
  disabled,
  state,
  onChange,
}: {
  categories: KnowledgeCategory[];
  disabled: boolean;
  state: KnowledgeEditorState;
  onChange: (state: KnowledgeEditorState) => void;
}) {
  function update<TKey extends keyof KnowledgeEditorState>(key: TKey, value: KnowledgeEditorState[TKey]) {
    onChange({ ...state, [key]: value });
  }

  return (
    <div className="knowledge-editor-fields">
      <FormField disabled={disabled} label="Заголовок" value={state.title} onChange={(value) => update("title", value)} />
      <FormField disabled={disabled} label="Краткое описание" value={state.description} onChange={(value) => update("description", value)} />
      <label className="knowledge-editor-field knowledge-category-select">
        <span>Категория</span>
        <div>
          <Icon name="folder" size={15} />
          <select disabled={disabled} value={state.categoryId ?? ""} onChange={(event) => update("categoryId", event.target.value ? Number(event.target.value) : null)}>
            <option value="">Выберите категорию</option>
            {categories.map((category) => (
              <option value={category.id} key={category.id}>
                {knowledgeCategoryPath(categories, category.id) || category.name}
              </option>
            ))}
          </select>
          <Icon name="chevron" size={14} />
        </div>
      </label>
      <label className="knowledge-content-field">
        <span>Содержимое (Markdown)</span>
        <textarea disabled={disabled} value={state.content} rows={10} onChange={(event) => update("content", event.target.value)} />
      </label>
    </div>
  );
}

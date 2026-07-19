import { Icon } from "../../../shared/icons";
import { FormField } from "../../../shared/form-controls";
import type { KnowledgeEditorState } from "./knowledgeEditorModel";
import { knowledgeCategoryPath } from "./knowledgeTree";
import { KnowledgeDepartmentPicker } from "./KnowledgeDepartmentPicker";
import type { KnowledgeCategory, KnowledgeDepartmentReference, KnowledgeVisibility } from "./types";

export function KnowledgeEditorFields({
  categories,
  departments,
  disabled,
  state,
  onChange,
}: {
  categories: KnowledgeCategory[];
  departments: KnowledgeDepartmentReference[];
  disabled: boolean;
  state: KnowledgeEditorState;
  onChange: (state: KnowledgeEditorState) => void;
}) {
  function update<TKey extends keyof KnowledgeEditorState>(key: TKey, value: KnowledgeEditorState[TKey]) {
    onChange({ ...state, [key]: value });
  }

  function setVisibility(visibility: KnowledgeVisibility) {
    onChange({
      ...state,
      visibility,
      departmentIds: visibility === "ORGANIZATION" ? [] : state.departmentIds,
    });
  }

  return (
    <div className="knowledge-editor-fields">
      <FormField disabled={disabled} label="Заголовок" value={state.title} onChange={(value) => update("title", value)} />
      <FormField disabled={disabled} label="Краткое описание" value={state.description} onChange={(value) => update("description", value)} />
      <div className="knowledge-editor-scope-row">
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
        <div className="knowledge-editor-field">
          <span>Область доступности</span>
          <div className="knowledge-visibility-segmented">
            <button className={state.visibility === "ORGANIZATION" ? "active" : ""} disabled={disabled} type="button" onClick={() => setVisibility("ORGANIZATION")}>Организация</button>
            <button className={state.visibility === "DEPARTMENTS" ? "active" : ""} disabled={disabled} type="button" onClick={() => setVisibility("DEPARTMENTS")}>Отделы</button>
          </div>
        </div>
      </div>
      {state.visibility === "DEPARTMENTS" && (
        <KnowledgeDepartmentPicker
          departments={departments}
          disabled={disabled}
          selectedIds={state.departmentIds}
          onChange={(departmentIds) => update("departmentIds", departmentIds)}
        />
      )}
      <label className="knowledge-content-field">
        <span>Содержимое (Markdown)</span>
        <textarea disabled={disabled} value={state.content} rows={10} onChange={(event) => update("content", event.target.value)} />
      </label>
    </div>
  );
}

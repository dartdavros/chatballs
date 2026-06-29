import { useState } from "react";

import { Button } from "../../../shared/ui-controls";
import { createDoc, type CreateDocInput, type DocKind } from "./docApi";

type DocCreateFormProps = {
  kind: DocKind;
  categories: Array<{ value: string; label: string }>;
  product: { code: string; name: string } | null;
  withInclusion?: boolean;
  onCreated: () => void;
};

export function DocCreateForm({ kind, categories, product, withInclusion = false, onCreated }: DocCreateFormProps) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState(categories[0]?.value ?? "");
  const [content, setContent] = useState("");
  // Знания можно делать глобальными или привязать к продукту канала; промпт всегда в скоупе канала.
  const [scope, setScope] = useState<"GLOBAL" | "PRODUCT">(product ? "PRODUCT" : "GLOBAL");
  const [inclusion, setInclusion] = useState<"MANDATORY" | "RETRIEVAL">("RETRIEVAL");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setTitle("");
    setCategory(categories[0]?.value ?? "");
    setContent("");
    setScope(product ? "PRODUCT" : "GLOBAL");
    setInclusion("RETRIEVAL");
    setError(null);
  }

  async function submit() {
    if (!title.trim()) {
      setError("Укажите название");
      return;
    }
    // Промпт всегда привязан к продукту канала (или глобальный, если у канала нет продукта).
    const effectiveScope = kind === "prompts" ? (product ? "PRODUCT" : "GLOBAL") : scope;
    const input: CreateDocInput = {
      title: title.trim(),
      category,
      content,
      scope: effectiveScope,
      ...(effectiveScope === "PRODUCT" && product ? { product: product.code } : {}),
      ...(withInclusion ? { inclusionMode: inclusion } : {}),
    };
    setBusy(true);
    setError(null);
    try {
      await createDoc(kind, input);
      reset();
      setOpen(false);
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось создать");
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <div className="ai-doc-add">
        <Button variant="secondary" icon="plus" onClick={() => setOpen(true)}>
          {kind === "knowledge" ? "Добавить материал" : "Добавить инструкцию"}
        </Button>
      </div>
    );
  }

  return (
    <section className="ai-card ai-doc-form">
      <div className="ai-doc-form-row">
        <label>
          <span>Название</span>
          <input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Например, Тарифы и оплата" />
        </label>
        <label>
          <span>Категория</span>
          <select value={category} onChange={(event) => setCategory(event.target.value)}>
            {categories.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </label>
      </div>

      {(kind === "knowledge" && product) || withInclusion ? (
        <div className="ai-doc-form-row">
          {kind === "knowledge" && product && (
            <label>
              <span>Область</span>
              <select value={scope} onChange={(event) => setScope(event.target.value as "GLOBAL" | "PRODUCT")}>
                <option value="PRODUCT">{product.name}</option>
                <option value="GLOBAL">Глобально (вся компания)</option>
              </select>
            </label>
          )}
          {withInclusion && (
            <label>
              <span>Включение</span>
              <select value={inclusion} onChange={(event) => setInclusion(event.target.value as "MANDATORY" | "RETRIEVAL")}>
                <option value="RETRIEVAL">По релевантности (поиск)</option>
                <option value="MANDATORY">Всегда в контексте</option>
              </select>
            </label>
          )}
        </div>
      ) : null}

      <textarea className="ai-doc-textarea" value={content} rows={8} placeholder="Содержимое" onChange={(event) => setContent(event.target.value)} />
      {error && <div className="ai-doc-error">{error}</div>}
      <div className="ai-doc-actions">
        <Button variant="secondary" disabled={busy} onClick={() => { reset(); setOpen(false); }}>Отмена</Button>
        <Button variant="primary" icon="plus" disabled={busy} onClick={submit}>Создать черновик</Button>
      </div>
    </section>
  );
}

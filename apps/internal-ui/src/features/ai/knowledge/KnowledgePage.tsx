import { Modal } from "antd";
import { useEffect, useMemo, useState } from "react";

import { Icon } from "../../../shared/icons";
import { FormField } from "../../../shared/form-controls";
import { EmptyState, LoadingState, PageHeader, StatusPill } from "../../../shared/ui";
import { Button, SearchInput } from "../../../shared/ui-controls";
import { formatDate } from "../../../shared/utils";
import { createKnowledgeItem, fetchKnowledgeList, formatSize, importKnowledge, type KnowledgeImportReport, type KnowledgeItem } from "./model";
import { parseKnowledgeYaml, type ParsedKnowledgeYaml } from "./parseKnowledgeYaml";

export function KnowledgePage({ openKnowledge }: { openKnowledge: (knowledgeId: number) => void }) {
  const [items, setItems] = useState<KnowledgeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [query, setQuery] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);

  async function load() {
    setError(false);
    try {
      const payload = await fetchKnowledgeList();
      setItems(payload.items);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return items;
    return items.filter((item) => item.title.toLowerCase().includes(needle) || item.description.toLowerCase().includes(needle));
  }, [items, query]);

  if (loading) return <div className="ai-page"><LoadingState /></div>;

  return (
    <div className="ai-page">
      <PageHeader
        title="Знания"
        text="Общая библиотека знаний · агент выбирает нужные знания в своей карточке"
        action={(
          <div className="knowledge-header-actions">
            <Button variant="secondary" icon="download" onClick={() => setImportOpen(true)}>Импорт YAML</Button>
            <Button variant="primary" icon="plus" onClick={() => setCreateOpen(true)}>Создать знание</Button>
          </div>
        )}
      />
      <div className="knowledge-toolbar">
        <SearchInput placeholder="Поиск по заголовку и описанию" value={query} onChange={setQuery} />
      </div>
      {error && <EmptyState title="Не удалось загрузить знания" />}
      {!error && filtered.length === 0 && <EmptyState title={query ? "Ничего не найдено" : "Знаний пока нет"} />}
      {!error && filtered.length > 0 && (
        <div className="table-card">
          <table className="baseline-table">
            <thead>
              <tr>
                <th>ЗНАНИЕ</th>
                <th className="numeric">ВЛОЖЕНИЯ</th>
                <th className="numeric">АГЕНТЫ</th>
                <th>СТАТУС</th>
                <th>ОБНОВЛЕНО</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => (
                <tr key={item.id} className="knowledge-row" onClick={() => openKnowledge(item.id)}>
                  <td>
                    <div className="product-cell">
                      <span className="product-icon knowledge-icon"><Icon name="list" size={19} /></span>
                      <span>
                        <button className="ai-agent-name-link" type="button" onClick={(event) => { event.stopPropagation(); openKnowledge(item.id); }}>{item.title}</button>
                        <small>{item.description || "—"}</small>
                      </span>
                    </div>
                  </td>
                  <td className="numeric">
                    {item.attachments.length > 0
                      ? `${item.attachments.length} · ${formatSize(item.attachments.reduce((sum, attachment) => sum + attachment.size, 0))}`
                      : <span className="product-empty-value">—</span>}
                  </td>
                  <td className="numeric">{item.agentsCount || <span className="product-empty-value">—</span>}</td>
                  <td><StatusPill status={item.isEnabled ? "active" : "disabled"} /></td>
                  <td>{formatDate(item.updatedAt)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="ai-table-footer">
            <span>{filtered.length} знаний</span>
            <span>Изменения знаний применяются к агентам сразу</span>
          </div>
        </div>
      )}
      {createOpen && <KnowledgeCreateModal onClose={() => setCreateOpen(false)} onCreated={(id) => { setCreateOpen(false); void load(); openKnowledge(id); }} />}
      {importOpen && <KnowledgeImportModal onClose={() => setImportOpen(false)} onImported={() => void load()} />}
    </div>
  );
}

function KnowledgeCreateModal({ onClose, onCreated }: { onClose: () => void; onCreated: (id: number) => void }) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [content, setContent] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!title.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const { knowledge } = await createKnowledgeItem({ title: title.trim(), description: description.trim(), content });
      onCreated(knowledge.id);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось создать знание");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open title="Создать знание" onCancel={onClose} footer={null} destroyOnClose>
      <div className="integration-form">
        <FormField label="Заголовок" value={title} onChange={setTitle} placeholder="например, FoxRay — тарифы" />
        <FormField label="Краткое описание" value={description} onChange={setDescription} placeholder="о чём это знание — агент видит описание в каталоге" />
        <label className="knowledge-content-field">
          <span>Содержимое (Markdown)</span>
          <textarea value={content} rows={10} onChange={(event) => setContent(event.target.value)} placeholder="Текст знания. Можно ссылаться на вложения по имени файла." />
        </label>
        {error && <div className="integration-form-error">{error}</div>}
        <div className="integration-form-actions">
          <Button variant="secondary" onClick={onClose}>Отмена</Button>
          <Button variant="primary" disabled={!title.trim() || busy} onClick={submit}>{busy ? "Создание…" : "Создать"}</Button>
        </div>
      </div>
    </Modal>
  );
}

function KnowledgeImportModal({ onClose, onImported }: { onClose: () => void; onImported: () => void }) {
  const [parsed, setParsed] = useState<ParsedKnowledgeYaml | null>(null);
  const [result, setResult] = useState<KnowledgeImportReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setError(null);
    setResult(null);
    try {
      setParsed(parseKnowledgeYaml(await file.text()));
    } catch (caught) {
      setParsed(null);
      setError(caught instanceof Error ? caught.message : "Не удалось прочитать файл");
    }
  }

  async function submit() {
    if (!parsed) return;
    setBusy(true);
    setError(null);
    try {
      setResult(await importKnowledge(parsed.documents));
      setParsed(null);
      onImported();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось импортировать");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open title="Импорт знаний из YAML" onCancel={onClose} footer={null} destroyOnClose>
      <div className="integration-form">
        <label className="knowledge-import-file">
          <span>Файл YAML · формат: documents: [{"{"} title, description?, content {"}"}]</span>
          <input type="file" accept=".yaml,.yml" onChange={(event) => void onFile(event)} />
        </label>
        {parsed && <div className="ai-doc-import-preview">К импорту: <b>{parsed.documents.length}</b> знаний. Совпадение по заголовку обновит существующее знание.</div>}
        {result && (
          <div className="ai-doc-import-report">
            <div className="ai-doc-import-summary">
              Создано: <b>{result.created}</b> · Обновлено: <b>{result.updated}</b> · Без изменений: <b>{result.unchanged}</b>
            </div>
            {result.failed.length > 0 && (
              <ul className="ai-doc-import-failed">
                {result.failed.map((item, index) => (
                  <li key={index}>{item.title ? `«${item.title}»: ` : ""}{item.detail}</li>
                ))}
              </ul>
            )}
          </div>
        )}
        {error && <div className="ai-doc-error">{error}</div>}
        <div className="integration-form-actions">
          <Button variant="secondary" disabled={busy} onClick={onClose}>Закрыть</Button>
          <Button variant="primary" icon="download" disabled={!parsed || busy} onClick={submit}>{busy ? "Импорт…" : "Импорт"}</Button>
        </div>
      </div>
    </Modal>
  );
}

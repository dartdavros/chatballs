import { Modal } from "antd";
import { useState } from "react";

import { Icon } from "../../../shared/icons";
import { Button } from "../../../shared/ui-controls";
import { pluralRu } from "../../../shared/utils";
import { categoryRows } from "./knowledgeLibraryModel";
import { knowledgeCategoryPath } from "./knowledgeTree";
import type { KnowledgeCategory } from "./types";

// «Переместить в категорию» из панели массовых операций (кадр KB2). Категории
// не создаются на лету: список — то же дерево, что и слева в библиотеке.

export function KnowledgeCategoryDialog({
  busy,
  categories,
  count,
  onCancel,
  onSubmit,
}: {
  busy: boolean;
  categories: KnowledgeCategory[];
  count: number;
  onCancel: () => void;
  onSubmit: (categoryId: number) => void;
}) {
  const rows = categoryRows(categories);
  const [categoryId, setCategoryId] = useState<number | null>(rows[0]?.category.id ?? null);

  return (
    <Modal className="knowledge-move-dialog" open width={480} title={null} footer={null} closable={false} onCancel={onCancel} destroyOnHidden>
      <header className="knowledge-agent-dialog-head">
        <div className="knowledge-agent-dialog-title">
          <div>
            <h3>Переместить в категорию</h3>
            <p>Выбрано {pluralRu(count, ["знание", "знания", "знаний"])}. Категория задаёт размещение в дереве, на ответы агента она не влияет.</p>
          </div>
          <button aria-label="Закрыть" className="knowledge-dialog-close" title="Закрыть" type="button" onClick={onCancel}>
            <Icon name="close" size={15} strokeWidth={2.2} />
          </button>
        </div>
      </header>

      <div className="knowledge-agent-dialog-body">
        <span className="knowledge-agent-dialog-label">КАТЕГОРИЯ</span>
        <div className="knowledge-move-list">
          {rows.map(({ category, depth, count: knowledgeCount }) => (
            <button
              className={`knowledge-move-row${category.id === categoryId ? " is-picked" : ""}`}
              key={category.id}
              style={{ paddingLeft: 11 + depth * 16 }}
              title={knowledgeCategoryPath(categories, category.id)}
              type="button"
              onClick={() => setCategoryId(category.id)}
            >
              <i className="knowledge-agent-radio"><b /></i>
              <span>{category.name}</span>
              <small>{knowledgeCount}</small>
            </button>
          ))}
        </div>
      </div>

      <footer className="knowledge-agent-dialog-foot">
        <span />
        <Button variant="secondary" disabled={busy} onClick={onCancel}>Отмена</Button>
        <Button variant="primary" disabled={busy || categoryId === null} onClick={() => categoryId !== null && onSubmit(categoryId)}>
          Переместить
        </Button>
      </footer>
    </Modal>
  );
}

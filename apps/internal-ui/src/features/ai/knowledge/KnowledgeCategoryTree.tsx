import { useEffect, useRef, useState } from "react";

import { Icon } from "../../../shared/icons";
import { buildKnowledgeCategoryTree, totalKnowledgeCount, type KnowledgeCategoryNode } from "./knowledgeTree";
import type { KnowledgeCategory } from "./types";

type KnowledgeCategoryTreeProps = {
  canManage: boolean;
  categories: KnowledgeCategory[];
  error: boolean;
  loading: boolean;
  onManage: () => void;
  onRetry: () => void;
  onSelect: (categoryId: number | undefined) => void;
  selectedId?: number;
};

function CategoryRows({
  expanded,
  level,
  nodes,
  onSelect,
  selectedId,
  toggleExpanded,
}: {
  expanded: Set<number>;
  level: number;
  nodes: KnowledgeCategoryNode[];
  onSelect: (categoryId: number) => void;
  selectedId?: number;
  toggleExpanded: (categoryId: number) => void;
}) {
  return nodes.map((category) => {
    const hasChildren = category.children.length > 0;
    const isExpanded = expanded.has(category.id);
    return (
      <div key={category.id}>
        <div
          className={`knowledge-category-row${selectedId === category.id ? " active" : ""}`}
          style={{ paddingLeft: 10 + level * 20 }}
        >
          {hasChildren ? (
            <button
              aria-label={isExpanded ? `Свернуть ${category.name}` : `Развернуть ${category.name}`}
              className={`knowledge-category-chevron${isExpanded ? " expanded" : ""}`}
              type="button"
              onClick={() => toggleExpanded(category.id)}
            >
              <Icon name="chevron" size={14} />
            </button>
          ) : <span className="knowledge-category-chevron-spacer" />}
          {!hasChildren && <Icon name="folder" size={15} />}
          <button className="knowledge-category-name" type="button" onClick={() => onSelect(category.id)}>
            {category.name}
          </button>
          {category.isSystem && <span className="knowledge-system-badge">СИСТ.</span>}
          <span className="knowledge-category-count">{category.knowledgeCount ?? 0}</span>
        </div>
        {hasChildren && isExpanded && (
          <CategoryRows
            expanded={expanded}
            level={level + 1}
            nodes={category.children}
            onSelect={onSelect}
            selectedId={selectedId}
            toggleExpanded={toggleExpanded}
          />
        )}
      </div>
    );
  });
}

export function KnowledgeCategoryTree({
  canManage,
  categories,
  error,
  loading,
  onManage,
  onRetry,
  onSelect,
  selectedId,
}: KnowledgeCategoryTreeProps) {
  const [expanded, setExpanded] = useState<Set<number>>(() => new Set());
  const initialized = useRef(false);
  const tree = buildKnowledgeCategoryTree(categories);

  useEffect(() => {
    if (initialized.current || categories.length === 0) return;
    initialized.current = true;
    setExpanded(new Set(categories.filter((category) => (
      categories.some((item) => item.parentId === category.id)
    )).map((category) => category.id)));
  }, [categories]);

  function toggleExpanded(categoryId: number) {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(categoryId)) next.delete(categoryId);
      else next.add(categoryId);
      return next;
    });
  }

  return (
    <aside className="knowledge-category-tree">
      <header>
        <span>КАТЕГОРИИ</span>
        {canManage && (
          <button type="button" onClick={onManage}>
            <Icon name="plus" size={13} />Управление
          </button>
        )}
      </header>
      <div className="knowledge-category-tree-body">
        <button
          className={`knowledge-category-all${selectedId === undefined ? " active" : ""}`}
          type="button"
          onClick={() => onSelect(undefined)}
        >
          <span className="knowledge-category-active-mark" />
          <Icon name="folder" size={16} />
          <span>Все знания</span>
          <b>{totalKnowledgeCount(categories)}</b>
        </button>
        {loading ? (
          <div className="knowledge-category-state">Загрузка…</div>
        ) : error ? (
          <div className="knowledge-category-state">
            <span>Не удалось загрузить категории</span>
            <button type="button" onClick={onRetry}>Повторить</button>
          </div>
        ) : tree.length === 0 ? (
          <div className="knowledge-category-state">Категорий пока нет</div>
        ) : (
          <CategoryRows
            expanded={expanded}
            level={0}
            nodes={tree}
            onSelect={onSelect}
            selectedId={selectedId}
            toggleExpanded={toggleExpanded}
          />
        )}
      </div>
    </aside>
  );
}

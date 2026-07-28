import { useEffect, useMemo, useRef, useState } from "react";

import { Icon } from "../icons";

export type ContentCategory = {
  id: number;
  name: string;
  parentId: number | null;
  count: number;
  badge?: string;
};

type CategoryNode = ContentCategory & { children: CategoryNode[] };

function buildTree(categories: ContentCategory[]): CategoryNode[] {
  const nodes = new Map<number, CategoryNode>(
    categories.map((category) => [category.id, { ...category, children: [] }]),
  );
  const roots: CategoryNode[] = [];
  nodes.forEach((node) => {
    const parent = node.parentId === null ? undefined : nodes.get(node.parentId);
    if (parent) parent.children.push(node);
    else roots.push(node);
  });
  return roots;
}

function Rows({
  expanded,
  level,
  nodes,
  onSelect,
  selectedId,
  toggle,
}: {
  expanded: Set<number>;
  level: number;
  nodes: CategoryNode[];
  onSelect: (categoryId: number) => void;
  selectedId?: number;
  toggle: (categoryId: number) => void;
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
              onClick={() => toggle(category.id)}
            >
              <Icon name="chevron" size={14} />
            </button>
          ) : <span className="knowledge-category-chevron-spacer" />}
          {!hasChildren && <Icon name="folder" size={15} />}
          <button className="knowledge-category-name" type="button" onClick={() => onSelect(category.id)}>
            {category.name}
          </button>
          {category.badge && <span className="knowledge-system-badge">{category.badge}</span>}
          <span className="knowledge-category-count">{category.count}</span>
        </div>
        {hasChildren && isExpanded && (
          <Rows
            expanded={expanded}
            level={level + 1}
            nodes={category.children}
            onSelect={onSelect}
            selectedId={selectedId}
            toggle={toggle}
          />
        )}
      </div>
    );
  });
}

export function CategoryTree({
  allLabel,
  canManage,
  categories,
  error,
  loading,
  onManage,
  onRetry,
  onSelect,
  selectedId,
}: {
  allLabel: string;
  canManage: boolean;
  categories: ContentCategory[];
  error: boolean;
  loading: boolean;
  onManage: () => void;
  onRetry: () => void;
  onSelect: (categoryId: number | undefined) => void;
  selectedId?: number;
}) {
  const [expanded, setExpanded] = useState<Set<number>>(() => new Set());
  const initialized = useRef(false);
  const tree = useMemo(() => buildTree(categories), [categories]);
  const total = categories
    .filter((category) => category.parentId === null)
    .reduce((sum, category) => sum + category.count, 0);

  useEffect(() => {
    if (initialized.current || categories.length === 0) return;
    initialized.current = true;
    setExpanded(new Set(categories.filter((category) => (
      categories.some((item) => item.parentId === category.id)
    )).map((category) => category.id)));
  }, [categories]);

  function toggle(categoryId: number) {
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
        {canManage && <button type="button" onClick={onManage}><Icon name="plus" size={13} />Управление</button>}
      </header>
      <div className="knowledge-category-tree-body">
        <button
          className={`knowledge-category-all${selectedId === undefined ? " active" : ""}`}
          type="button"
          onClick={() => onSelect(undefined)}
        >
          <span className="knowledge-category-active-mark" />
          <Icon name="folder" size={16} />
          <span>{allLabel}</span>
          <b>{total}</b>
        </button>
        {loading ? <div className="knowledge-category-state">Загрузка…</div>
          : error ? <div className="knowledge-category-state"><span>Не удалось загрузить категории</span><button type="button" onClick={onRetry}>Повторить</button></div>
            : tree.length === 0 ? <div className="knowledge-category-state">Категорий пока нет</div>
              : <Rows expanded={expanded} level={0} nodes={tree} onSelect={onSelect} selectedId={selectedId} toggle={toggle} />}
      </div>
    </aside>
  );
}

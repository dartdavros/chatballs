import { useState } from "react";

import { hasCapability } from "../../../auth/access";
import { agentLinkOptions } from "../agentOptions";
import { useAiAgents } from "../useAiAgents";
import type { RouteKey, SessionUser } from "../../../types";
import { CategoryManagement } from "./CategoryManagement";
import { KnowledgeBulkActions } from "./KnowledgeBulkActions";
import { KnowledgeCategoryTree } from "./KnowledgeCategoryTree";
import { KnowledgeImportModal } from "./KnowledgeImportModal";
import { KnowledgePageHeader } from "./KnowledgePageHeader";
import { KnowledgeTable } from "./KnowledgeTable";
import { KnowledgeToolbar } from "./KnowledgeToolbar";
import { useKnowledgeLibrary } from "./useKnowledgeLibrary";

type KnowledgePageProps = {
  openKnowledge: (knowledgeId: number) => void;
  openAgent: (agentId: number) => void;
  setRoute: (route: RouteKey) => void;
  user: SessionUser;
};

export function KnowledgePage({ openAgent, openKnowledge, setRoute, user }: KnowledgePageProps) {
  const [importOpen, setImportOpen] = useState(false);
  const [categoryManagementOpen, setCategoryManagementOpen] = useState(false);
  const library = useKnowledgeLibrary();
  const { agents } = useAiAgents();
  const canManageKnowledge = hasCapability(user, "ai.manage");
  const bulkMode = library.selectedIds.size > 0;

  const hasActiveFilters = Boolean(
    library.filters.search.trim()
      || library.filters.isEnabled !== undefined,
  );

  return (
    <div className="ai-page">
      <KnowledgePageHeader
        canCreate={canManageKnowledge}
        canImport={canManageKnowledge}
        onCreate={() => setRoute("aiKnowledgeCreate")}
        onImport={() => setImportOpen(true)}
      />
      <div className={`knowledge-library-layout${bulkMode ? " bulk-mode" : ""}`}>
        {!bulkMode && <KnowledgeCategoryTree
          canManage={canManageKnowledge}
          categories={library.categories}
          error={library.categoriesError}
          loading={library.categoriesLoading}
          selectedId={library.filters.category}
          onManage={() => setCategoryManagementOpen(true)}
          onRetry={() => void library.reloadCategories()}
          onSelect={(categoryId) => library.updateFilter("category", categoryId)}
        />}
        <main className="knowledge-library-list">
          {bulkMode ? (
            <KnowledgeBulkActions
              agents={agentLinkOptions(agents)}
              canLinkAgents={canManageKnowledge}
              categories={library.categories}
              selectedIds={library.selectedIds}
              onClear={library.clearSelected}
              onComplete={async () => { await library.reload(); library.clearSelected(); }}
            />
          ) : (
            <KnowledgeToolbar
              isEnabled={library.filters.isEnabled}
              query={library.filters.search}
              onEnabledChange={(value) => library.updateFilter("isEnabled", value)}
              onQueryChange={(value) => library.updateFilter("search", value)}
            />
          )}
          <KnowledgeTable
            canCreate={canManageKnowledge}
            canSelect={canManageKnowledge}
            bulkMode={bulkMode}
            categories={library.categories}
            error={library.itemsError}
            hasActiveFilters={hasActiveFilters}
            items={library.items}
            loading={library.itemsLoading}
            openKnowledge={openKnowledge}
            selectedCategoryId={library.filters.category}
            selectedIds={library.selectedIds}
            onCreate={() => setRoute("aiKnowledgeCreate")}
            onRetry={() => void library.reload()}
            onToggleSelected={library.toggleSelected}
            onToggleVisible={library.toggleVisible}
          />
          {bulkMode && <p className="knowledge-bulk-note">Если часть выбранных знаний нельзя изменить, список останется без изменений. Выбор снимется после успешного сохранения.</p>}
        </main>
      </div>
      {categoryManagementOpen && (
        <CategoryManagement
          categories={library.categories}
          onChanged={library.reload}
          onClose={() => setCategoryManagementOpen(false)}
        />
      )}
      {importOpen && (
        <KnowledgeImportModal
          onClose={() => setImportOpen(false)}
          onImported={() => void library.reload()}
        />
      )}
    </div>
  );
}

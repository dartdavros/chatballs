import { useMemo, useState } from "react";

import { hasCapability } from "../../../auth/access";
import type { Department, SessionUser } from "../../../types";
import { CategoryManagement } from "./CategoryManagement";
import { KnowledgeCategoryTree } from "./KnowledgeCategoryTree";
import { KnowledgeCreateModal } from "./KnowledgeCreateModal";
import { KnowledgeImportModal } from "./KnowledgeImportModal";
import { KnowledgePageHeader } from "./KnowledgePageHeader";
import { KnowledgeTable } from "./KnowledgeTable";
import { KnowledgeToolbar } from "./KnowledgeToolbar";
import type { KnowledgeDepartmentReference } from "./types";
import { useKnowledgeLibrary } from "./useKnowledgeLibrary";

type KnowledgePageProps = {
  departments: Department[];
  openKnowledge: (knowledgeId: number) => void;
  user: SessionUser;
};

function canManageInAnyScope(user: SessionUser): boolean {
  return user.capabilities.includes("ai.manage")
    && user.accessScopes.some((scope) => scope.capabilities.includes("ai.manage"));
}

function KnowledgeAccessNotice({ departments, user }: { departments: Department[]; user: SessionUser }) {
  const organizationView = hasCapability(user, "ai.view");
  if (organizationView) return null;
  const departmentNames = user.accessScopes
    .filter((scope) => scope.scopeType === "DEPARTMENT" && scope.capabilities.includes("ai.view"))
    .map((scope) => departments.find((item) => item.id === scope.departmentId)?.name ?? scope.departmentCode)
    .filter((name): name is string => Boolean(name));
  if (departmentNames.length === 0) return null;
  return (
    <div className="knowledge-access-notice">
      <span>Доступ ограничен отделом</span>
      <p>Ваш доступ <code>ai.view</code> охватывает: {departmentNames.join(", ")}. Знания других отделов не показываются и недоступны для изменения.</p>
    </div>
  );
}

export function KnowledgePage({ departments, openKnowledge, user }: KnowledgePageProps) {
  const [createOpen, setCreateOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [categoryManagementOpen, setCategoryManagementOpen] = useState(false);
  const library = useKnowledgeLibrary();
  const canManageCategories = hasCapability(user, "ai.manage");
  const canManageKnowledge = canManageInAnyScope(user);

  const filterDepartments = useMemo(() => {
    const byId = new Map<number, KnowledgeDepartmentReference>();
    departments
      .filter((department) => department.status === "ACTIVE")
      .forEach((department) => byId.set(department.id, department));
    library.knownDepartments.forEach((department) => byId.set(department.id, department));
    return [...byId.values()].sort((left, right) => left.name.localeCompare(right.name, "ru"));
  }, [departments, library.knownDepartments]);

  const hasActiveFilters = Boolean(
    library.filters.search.trim()
      || library.filters.department !== undefined
      || library.filters.visibility !== undefined
      || library.filters.isEnabled !== undefined,
  );

  return (
    <div className="ai-page">
      <KnowledgePageHeader
        canCreate={canManageCategories}
        canImport={canManageKnowledge}
        onCreate={() => setCreateOpen(true)}
        onImport={() => setImportOpen(true)}
      />
      <KnowledgeAccessNotice departments={departments} user={user} />
      <div className="knowledge-library-layout">
        <KnowledgeCategoryTree
          canManage={canManageCategories}
          categories={library.categories}
          error={library.categoriesError}
          loading={library.categoriesLoading}
          selectedId={library.filters.category}
          onManage={() => setCategoryManagementOpen(true)}
          onRetry={() => void library.reloadCategories()}
          onSelect={(categoryId) => library.updateFilter("category", categoryId)}
        />
        <main className="knowledge-library-list">
          <KnowledgeToolbar
            department={library.filters.department}
            departments={filterDepartments}
            isEnabled={library.filters.isEnabled}
            query={library.filters.search}
            visibility={library.filters.visibility}
            onDepartmentChange={(value) => library.updateFilter("department", value)}
            onEnabledChange={(value) => library.updateFilter("isEnabled", value)}
            onQueryChange={(value) => library.updateFilter("search", value)}
            onVisibilityChange={(value) => library.updateFilter("visibility", value)}
          />
          <KnowledgeTable
            canCreate={canManageCategories}
            canSelect={canManageKnowledge}
            categories={library.categories}
            error={library.itemsError}
            hasActiveFilters={hasActiveFilters}
            items={library.items}
            loading={library.itemsLoading}
            openKnowledge={openKnowledge}
            selectedCategoryId={library.filters.category}
            selectedIds={library.selectedIds}
            onCreate={() => setCreateOpen(true)}
            onRetry={() => void library.reload()}
            onToggleSelected={library.toggleSelected}
            onToggleVisible={library.toggleVisible}
          />
        </main>
      </div>
      {categoryManagementOpen && (
        <CategoryManagement
          categories={library.categories}
          onChanged={library.reload}
          onClose={() => setCategoryManagementOpen(false)}
        />
      )}
      {createOpen && (
        <KnowledgeCreateModal
          initialCategoryId={library.filters.category}
          onClose={() => setCreateOpen(false)}
          onCreated={(id) => {
            setCreateOpen(false);
            void library.reload();
            openKnowledge(id);
          }}
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

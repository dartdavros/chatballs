import { useState } from "react";

import { LoadingState } from "../../../shared/ui";
import { KnowledgeCreateModal } from "./KnowledgeCreateModal";
import { KnowledgeImportModal } from "./KnowledgeImportModal";
import { KnowledgeTable } from "./KnowledgeTable";
import { KnowledgeToolbar } from "./KnowledgeToolbar";
import { useKnowledgeLibrary } from "./useKnowledgeLibrary";

export function KnowledgePage({ openKnowledge }: { openKnowledge: (knowledgeId: number) => void }) {
  const [createOpen, setCreateOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const library = useKnowledgeLibrary();

  if (library.loading) return <div className="ai-page"><LoadingState /></div>;

  return (
    <div className="ai-page">
      <KnowledgeToolbar
        query={library.query}
        onQueryChange={library.setQuery}
        onCreate={() => setCreateOpen(true)}
        onImport={() => setImportOpen(true)}
      />
      <KnowledgeTable
        items={library.filteredItems}
        error={library.error}
        query={library.query}
        openKnowledge={openKnowledge}
      />
      {createOpen && (
        <KnowledgeCreateModal
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

import { useEffect, useMemo, useState } from "react";

import { api } from "../../../api/client";
import { EmptyState, LoadingState } from "../../../shared/ui";
import type { RouteKey } from "../../../types";
import { ProductAIReleaseHeader } from "./ProductAIReleaseHeader";
import { PublishReleaseModal } from "./PublishReleaseModal";
import { ReleaseComposition } from "./ReleaseComposition";
import { ReleaseSidePanel, ReleaseValidationBanner } from "./ReleaseSidePanel";
import { buildChanges, buildChecks, canPublishRelease, findPublishedPeer, releaseLabel } from "./model";
import { useProductAIRelease } from "./useProductAIRelease";

export function ProductAIReleasePage({
  onReleaseLoaded,
  releaseId,
  setRoute,
}: {
  onReleaseLoaded: (name: string | null) => void;
  releaseId: number | null;
  setRoute: (route: RouteKey) => void;
}) {
  const { release, releases, knowledge, prompts, loading, error, reload } = useProductAIRelease(releaseId);
  const [modalOpen, setModalOpen] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [publishing, setPublishing] = useState(false);

  useEffect(() => {
    onReleaseLoaded(release ? `${release.product.name} Sales|${releaseLabel(release)}` : null);
    return () => onReleaseLoaded(null);
  }, [onReleaseLoaded, release]);

  const checks = useMemo(() => release ? buildChecks(release) : [], [release]);
  const published = useMemo(() => release ? findPublishedPeer(release, releases) : undefined, [release, releases]);
  const changes = useMemo(() => release ? buildChanges(release, published) : [], [release, published]);
  const canPublish = release ? canPublishRelease(release, checks) : false;

  async function publish() {
    if (!release || !confirmed) return;
    setPublishing(true);
    try {
      await api(`/api/v1/ai/releases/${release.id}/publish/`, { method: "POST" });
      setModalOpen(false);
      setConfirmed(false);
      reload();
    } catch {
      // API returns validation details; modal stays open so the user can retry after checks are refreshed.
    } finally {
      setPublishing(false);
    }
  }

  if (loading) return <div className="ai-release-state"><LoadingState /></div>;
  if (error || !release) return <div className="ai-release-state"><EmptyState title="Не удалось загрузить версию" /></div>;

  return (
    <div className="ai-release-page">
      <ProductAIReleaseHeader canPublish={canPublish} checks={checks} release={release} setRoute={setRoute} startPublish={() => setModalOpen(true)} />
      <div className="ai-release-body">
        <ReleaseValidationBanner checks={checks} runChecks={reload} />
        <div className="release-layout">
          <ReleaseComposition knowledge={knowledge} prompts={prompts} published={published} release={release} />
          <ReleaseSidePanel changes={changes} checks={checks} published={published} />
        </div>
      </div>
      {modalOpen && <PublishReleaseModal checked={confirmed} close={() => setModalOpen(false)} confirm={publish} publishing={publishing} release={release} setChecked={setConfirmed} />}
    </div>
  );
}

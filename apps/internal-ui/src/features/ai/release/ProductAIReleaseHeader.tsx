import { Icon } from "../../../shared/icons";
import { Button } from "../../../shared/ui-controls";
import type { RouteKey } from "../../../types";
import type { AiReleaseFull } from "../detail/model";
import { formatDateTime, releaseLabel, releaseState, type ReleaseCheck } from "./model";

export function ProductAIReleaseHeader({
  canPublish,
  checks,
  release,
  setRoute,
  startPublish,
}: {
  canPublish: boolean;
  checks: ReleaseCheck[];
  release: AiReleaseFull;
  setRoute: (route: RouteKey) => void;
  startPublish: () => void;
}) {
  const state = releaseState(checks, release.status === "PUBLISHED");
  const label = releaseLabel(release);
  return (
    <section className="release-status-bar">
      <div className="release-title-group">
        <span className="release-icon"><Icon name="robot" size={21} /></span>
        <div>
          <div className="release-title-row">
            <h1>{label}</h1>
            <span className={`release-status-badge ${state.className}`}>
              <span />
              {state.label}
            </span>
          </div>
          <div className="release-subtitle">
            {release.product.name} Sales · черновик создан {formatDateTime(release.createdAt)}
          </div>
        </div>
      </div>
      <div className="release-actions">
        <Button variant="secondary" icon="expand">Сравнить с опубликованной</Button>
        <Button variant="secondary" icon="message" onClick={() => setRoute("aiTestChat")}>Тест-чат</Button>
        <Button variant="primary" icon="send" disabled={!canPublish} onClick={startPublish}>
          {release.status === "PUBLISHED" ? "Опубликована" : "Опубликовать"}
        </Button>
      </div>
    </section>
  );
}

import { EmptyState } from "../../../shared/ui";
import { ToneBadge } from "../../../shared/ui-controls";
import { formatDate } from "../../../shared/utils";
import { releaseTone, type AiReleaseFull } from "./model";

export function AiAgentReleasesTab({ releases }: { releases: AiReleaseFull[] }) {
  if (releases.length === 0) {
    return <EmptyState title="Releases ещё не создавались" />;
  }
  return (
    <div className="table-card">
      <div className="ai-agents-scroll">
        <table className="baseline-table">
          <thead>
            <tr>
              <th>RELEASE</th>
              <th>СТАТУС</th>
              <th>ДАТА</th>
              <th>АВТОР</th>
              <th className="numeric">ДИАЛОГИ</th>
              <th className="numeric">КОНВЕРСИЯ</th>
            </tr>
          </thead>
          <tbody>
            {releases.map((release) => {
              const tone = releaseTone(release.status);
              return (
                <tr key={release.id}>
                  <td><code className="ai-mono">{`v${release.version}`}</code></td>
                  <td><ToneBadge bg={tone.bg} color={tone.color}>{tone.label}</ToneBadge></td>
                  <td>{formatDate(release.publishedAt ?? release.createdAt)}</td>
                  <td><span className="product-empty-value">—</span></td>
                  <td className="numeric"><span className="product-empty-value">—</span></td>
                  <td className="numeric"><span className="product-empty-value">—</span></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

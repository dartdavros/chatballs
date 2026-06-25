import type { AiReleaseFull } from "../detail/model";
import type { ReleaseChange, ReleaseCheck } from "./model";
import { checksSummary, releaseLabel, validationBanner } from "./model";

function toneClass(tone: string) {
  return `release-tone-${tone}`;
}

export function ReleaseValidationBanner({ checks, runChecks }: { checks: ReleaseCheck[]; runChecks: () => void }) {
  const banner = validationBanner(checks);
  const issue = checks.find((check) => check.tone === banner.tone) ?? checks[0];
  return (
    <div className={`release-validation ${toneClass(banner.tone)}`}>
      <span>{issue?.icon}</span>
      <div>
        <strong>{banner.title}</strong>
        <p>{banner.note}</p>
      </div>
      <button type="button" onClick={runChecks}>Запустить проверку</button>
    </div>
  );
}

export function ReleaseSidePanel({ changes, checks, published }: { changes: ReleaseChange[]; checks: ReleaseCheck[]; published?: AiReleaseFull }) {
  const summary = checksSummary(checks);
  return (
    <aside className="release-side">
      <section className="release-card release-card--flush">
        <div className="release-panel-head">
          <h3>Проверки</h3>
          <span className={toneClass(summary.tone)}>{summary.label}</span>
        </div>
        {checks.map((check) => (
          <div className="release-check-row" key={check.label}>
            <span className={toneClass(check.tone)}>{check.icon}</span>
            <div>
              <strong>{check.label}</strong>
              {check.detail && <small>{check.detail}</small>}
            </div>
          </div>
        ))}
      </section>

      <section className="release-card release-card--flush">
        <div className="release-panel-head release-panel-head--stack">
          <h3>Изменения</h3>
          <small>Относительно {published ? `${releaseLabel(published)} (опубликованная)` : "опубликованной версии"}</small>
        </div>
        {changes.map((change) => (
          <div className="release-change-row" key={change.text}>
            <span className={toneClass(change.tone)}>{change.sign}</span>
            <p>{change.text}</p>
          </div>
        ))}
      </section>
    </aside>
  );
}

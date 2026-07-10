import type { ReactNode } from "react";

import { Icon } from "../../../shared/icons";
import { dailyBudget, type AiReleaseFull, type KnowledgeDoc, type PromptDoc } from "../detail/model";
import { formatParam, isPromptChanged, knowledgeTitle, promptTitle, promptVersionDate, toolLabel } from "./model";

function ReleaseCard({ children, className = "", title, icon }: { children: ReactNode; className?: string; icon?: ReactNode; title: string }) {
  return (
    <section className={`release-card ${className}`.trim()}>
      <div className="release-card-title">
        {icon}
        <h3>{title}</h3>
      </div>
      {children}
    </section>
  );
}

function VersionRow({ changed, date, title, version }: { changed?: boolean; date?: string; title: string; version: number }) {
  return (
    <div className="release-row">
      <span>{title}</span>
      {changed && <b className="release-changed-badge">изменён</b>}
      {date && <small className="release-row-date">{date}</small>}
      <code className="ai-mono">{`v${version}`}</code>
    </div>
  );
}

export function ReleaseComposition({ knowledge, prompts, published, release }: { knowledge: KnowledgeDoc[]; prompts: PromptDoc[]; published?: AiReleaseFull; release: AiReleaseFull }) {
  const modelParams = release.modelParams ?? {};
  const tools = release.allowedTools.map(toolLabel).filter((tool) => tool !== "—");
  const budget = dailyBudget(release.limits ?? {});

  return (
    <div className="release-composition">
      <h2>Состав release</h2>
      <ReleaseCard title="Модель и параметры" icon={<Icon name="robot" size={17} />}>
        <div className="release-param-grid">
          <div><span>Модель</span><code className="ai-mono">{release.model || <EmptyMarker />}</code></div>
          <div><span>Temperature</span><code className="ai-mono">{formatParam(modelParams.temperature)}</code></div>
          <div><span>Max tokens</span><code className="ai-mono">{formatParam(modelParams.maxTokens)}</code></div>
          <div><span>Top-p</span><code className="ai-mono">{formatParam(modelParams.topP)}</code></div>
        </div>
      </ReleaseCard>

      <ReleaseCard title="Версии prompts" icon={<Icon name="list" size={17} />} className="release-card--flush">
        {release.promptVersions.length === 0 ? (
          <EmptyRow />
        ) : (
          release.promptVersions.map((prompt) => (
            <VersionRow
              changed={isPromptChanged(published, prompt.document, prompt.version)}
              date={promptVersionDate(prompts, prompt.document, prompt.version)}
              key={`${prompt.document}-${prompt.version}`}
              title={promptTitle(prompts, prompt.document)}
              version={prompt.version}
            />
          ))
        )}
      </ReleaseCard>

      <ReleaseCard title="Обязательные знания" icon={<Icon name="paperclip" size={17} />} className="release-card--flush release-knowledge-card">
        <div className="release-index-line">retrieval index · <b>{release.retrievalIndexVersion ? "собран" : "не собран"}</b></div>
        {release.knowledgeVersions.length === 0 ? (
          <EmptyRow />
        ) : (
          release.knowledgeVersions.map((document) => (
            <div className="release-row release-knowledge-row" key={`${document.document}-${document.version}`}>
              <Icon name="check" size={15} />
              <span>{knowledgeTitle(knowledge, document.document)}</span>
              <code className="ai-mono">{`v${document.version}`}</code>
            </div>
          ))
        )}
      </ReleaseCard>

      <div className="release-double-grid">
        <ReleaseCard title="Инструменты">
          {tools.length === 0 ? (
            <EmptyRow compact />
          ) : (
            <div className="release-tools">
              {tools.map((tool) => <div key={tool}><Icon name="check" size={14} /><code className="ai-mono">{tool}</code></div>)}
            </div>
          )}
        </ReleaseCard>
        <ReleaseCard title="Лимиты">
          {budget === "—" ? (
            <EmptyRow compact />
          ) : (
            <div className="release-limit-line">
              <span>Бюджет в день</span>
              <b>{budget}</b>
            </div>
          )}
        </ReleaseCard>
      </div>
    </div>
  );
}

function EmptyMarker() {
  return <span className="release-empty-marker">—</span>;
}

function EmptyRow({ compact = false }: { compact?: boolean }) {
  return <div className={compact ? "release-empty-line compact" : "release-empty-line"}><EmptyMarker /></div>;
}

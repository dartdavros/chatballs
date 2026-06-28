import { useState, type ReactNode } from "react";

import { Icon } from "../../../shared/icons";
import { Button } from "../../../shared/ui-controls";
import { formatDate } from "../../../shared/utils";
import { hasUnpublishedDraft, latestVersion, publishVersion, saveDocVersion, setDocEnabled, type DocKind } from "./docApi";
import { publishedVersion, type DocVersion } from "./model";

type DocCardProps = {
  kind: DocKind;
  index: number;
  id: number;
  title: string;
  category: string;
  isEnabled: boolean;
  versions: DocVersion[];
  meta?: ReactNode;
  onChanged: () => void;
};

export function DocCard({ kind, index, id, title, category, isEnabled, versions, meta, onChanged }: DocCardProps) {
  const published = publishedVersion(versions);
  const latest = latestVersion(versions);
  const pendingDraft = hasUnpublishedDraft(versions);

  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function startEdit() {
    setDraft(latest?.content ?? "");
    setError(null);
    setEditing(true);
  }

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      setEditing(false);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось сохранить");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="ai-card ai-doc-card">
      <div className="ai-instruction-head">
        <span className="ai-instruction-index">{index}</span>
        <h3>{title}</h3>
        <small>{category}</small>
        <div className="ai-doc-status">
          {meta}
          {published ? (
            <span className="ai-doc-chip on">Опубликовано v{published.version}</span>
          ) : (
            <span className="ai-doc-chip off">Не опубликовано</span>
          )}
          {pendingDraft && <span className="ai-doc-chip draft">Черновик v{latest?.version}</span>}
          {!isEnabled && <span className="ai-doc-chip off">Выключено</span>}
        </div>
      </div>

      {editing ? (
        <>
          <textarea className="ai-doc-textarea" value={draft} rows={10} onChange={(event) => setDraft(event.target.value)} />
          {error && <div className="ai-doc-error">{error}</div>}
          <div className="ai-doc-actions">
            <Button variant="secondary" disabled={busy} onClick={() => setEditing(false)}>Отмена</Button>
            <Button variant="secondary" icon="save" disabled={busy} onClick={() => run(() => saveDocVersion(kind, id, draft, false))}>
              Сохранить черновик
            </Button>
            <Button variant="primary" icon="check" disabled={busy} onClick={() => run(() => saveDocVersion(kind, id, draft, true))}>
              Сохранить и опубликовать
            </Button>
          </div>
        </>
      ) : (
        <>
          <pre className="ai-prompt-block">{(published ?? latest)?.content?.trim() || "—"}</pre>
          <div className="ai-doc-actions">
            <Button variant="secondary" icon="edit" onClick={startEdit}>Редактировать</Button>
            {pendingDraft && latest && (
              <Button variant="primary" icon="check" disabled={busy} onClick={() => run(() => publishVersion(kind, id, latest.version))}>
                Опубликовать черновик v{latest.version}
              </Button>
            )}
            <Button variant="secondary" icon={isEnabled ? "eyeOff" : "eye"} disabled={busy} onClick={() => run(() => setDocEnabled(kind, id, !isEnabled))}>
              {isEnabled ? "Выключить" : "Включить"}
            </Button>
            {latest && <span className="ai-doc-updated">обновлено {formatDate(latest.createdAt)}</span>}
          </div>
          {error && <div className="ai-doc-error">{error}</div>}
        </>
      )}
    </section>
  );
}

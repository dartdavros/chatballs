import { useState } from "react";

import { Button } from "../../../shared/ui-controls";
import { importDocs, type DocKind, type ImportResult } from "./docApi";
import { parseDocYaml } from "./parseDocYaml";

type DocImportFormProps = {
  kind: DocKind;
  onImported: () => void;
};

export function DocImportForm({ kind, onImported }: DocImportFormProps) {
  const [open, setOpen] = useState(false);
  const [preview, setPreview] = useState<{ count: number; product: string | null } | null>(null);
  const [parsed, setParsed] = useState<ReturnType<typeof parseDocYaml> | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setPreview(null);
    setParsed(null);
    setResult(null);
    setError(null);
  }

  async function onFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setError(null);
    setResult(null);
    try {
      const text = await file.text();
      const data = parseDocYaml(text);
      setParsed(data);
      setPreview({ count: data.documents.length, product: data.product });
    } catch (caught) {
      setParsed(null);
      setPreview(null);
      setError(caught instanceof Error ? caught.message : "Не удалось прочитать файл");
    }
  }

  async function submit() {
    if (!parsed) return;
    setBusy(true);
    setError(null);
    try {
      const report = await importDocs(kind, parsed.product, parsed.documents);
      setResult(report);
      setParsed(null);
      setPreview(null);
      onImported();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось импортировать");
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <div className="ai-doc-add">
        <Button variant="secondary" icon="download" onClick={() => setOpen(true)}>
          Импорт YAML
        </Button>
      </div>
    );
  }

  return (
    <section className="ai-card ai-doc-form">
      <div className="ai-doc-form-row">
        <label>
          <span>Файл YAML</span>
          <input type="file" accept=".yaml,.yml" onChange={(event) => void onFile(event)} />
        </label>
      </div>
      {preview && (
        <div className="ai-doc-import-preview">
          К импорту: <b>{preview.count}</b> документ(ов){preview.product ? `, продукт «${preview.product}»` : ", глобально"}.
        </div>
      )}
      {result && (
        <div className="ai-doc-import-report">
          <div className="ai-doc-import-summary">
            Создано: <b>{result.created}</b> · Обновлено: <b>{result.updated}</b> · Без изменений: <b>{result.unchanged}</b>
          </div>
          {result.failed.length > 0 && (
            <ul className="ai-doc-import-failed">
              {result.failed.map((item, index) => (
                <li key={index}>{item.code ? `«${item.code}»: ` : ""}{item.detail}</li>
              ))}
            </ul>
          )}
        </div>
      )}
      {error && <div className="ai-doc-error">{error}</div>}
      <div className="ai-doc-actions">
        <Button variant="secondary" disabled={busy} onClick={() => { reset(); setOpen(false); }}>Закрыть</Button>
        <Button variant="primary" icon="download" disabled={!parsed || busy} onClick={submit}>{busy ? "Импорт…" : "Импорт"}</Button>
      </div>
    </section>
  );
}

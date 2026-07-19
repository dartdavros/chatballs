import { Modal } from "antd";
import { useState } from "react";

import { Button } from "../../../shared/ui-controls";
import { importKnowledge, type KnowledgeImportReport } from "./model";
import { parseKnowledgeYaml, type ParsedKnowledgeYaml } from "./parseKnowledgeYaml";

type KnowledgeImportModalProps = {
  onClose: () => void;
  onImported: () => void;
};

export function KnowledgeImportModal({ onClose, onImported }: KnowledgeImportModalProps) {
  const [parsed, setParsed] = useState<ParsedKnowledgeYaml | null>(null);
  const [result, setResult] = useState<KnowledgeImportReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setError(null);
    setResult(null);
    try {
      setParsed(parseKnowledgeYaml(await file.text()));
    } catch (caught) {
      setParsed(null);
      setError(caught instanceof Error ? caught.message : "Не удалось прочитать файл");
    }
  }

  async function submit() {
    if (!parsed) return;
    setBusy(true);
    setError(null);
    try {
      setResult(await importKnowledge(parsed.documents));
      setParsed(null);
      onImported();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось импортировать");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open title="Импорт знаний из YAML" onCancel={onClose} footer={null} destroyOnClose>
      <div className="integration-form">
        <label className="knowledge-import-file">
          <span>Файл YAML · формат: documents: [{"{"} title, description?, content {"}"}]</span>
          <input type="file" accept=".yaml,.yml" onChange={(event) => void onFile(event)} />
        </label>
        {parsed && (
          <div className="ai-doc-import-preview">
            К импорту: <b>{parsed.documents.length}</b> знаний. Совпадение по заголовку обновит существующее знание.
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
                  <li key={index}>{item.title ? `«${item.title}»: ` : ""}{item.detail}</li>
                ))}
              </ul>
            )}
          </div>
        )}
        {error && <div className="ai-doc-error">{error}</div>}
        <div className="integration-form-actions">
          <Button variant="secondary" disabled={busy} onClick={onClose}>Закрыть</Button>
          <Button variant="primary" icon="download" disabled={!parsed || busy} onClick={submit}>
            {busy ? "Импорт…" : "Импорт"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}

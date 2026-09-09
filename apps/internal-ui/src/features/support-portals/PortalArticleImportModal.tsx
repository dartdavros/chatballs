import { Modal } from "antd";
import { useState } from "react";

import { Icon } from "../../shared/icons";
import { Button } from "../../shared/ui-controls";
import type { ArticleImportReport } from "./api";
import { downloadArticleTemplate } from "./downloadArticleTemplate";
import { importPortalArticles, portalErrorMessage } from "./model";
import { parseArticleYaml, type ParsedArticleYaml } from "./parseArticleYaml";
import { t } from "../../i18n";

type PortalArticleImportModalProps = {
  portalId: number;
  onClose: () => void;
  onImported: () => void;
};

export function PortalArticleImportModal({ portalId, onClose, onImported }: PortalArticleImportModalProps) {
  const [parsed, setParsed] = useState<ParsedArticleYaml | null>(null);
  const [result, setResult] = useState<ArticleImportReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setError(null);
    setResult(null);
    try {
      setParsed(parseArticleYaml(await file.text()));
    } catch (caught) {
      setParsed(null);
      setError(caught instanceof Error ? caught.message : t("ai.could_not_read_file"));
    }
  }

  async function submit() {
    if (!parsed) return;
    setBusy(true);
    setError(null);
    try {
      setResult(await importPortalArticles(portalId, parsed.articles));
      setParsed(null);
      onImported();
    } catch (caught) {
      setError(portalErrorMessage(caught, t("portals.could_not_import_articles")));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open title={t("portals.import_articles_from_yaml")} onCancel={onClose} footer={null} destroyOnClose>
      <div className="integration-form">
        <label className="knowledge-import-file">
          <span>
            {t("portals.yaml_format_note", { format: "{ slug, categoryPath, locale?, title, summary?, content }" })}
            <button className="link has-icon" type="button" onClick={downloadArticleTemplate}>
              <Icon name="download" size={14} />{t("portals.download_template")}</button>
          </span>
          <input type="file" accept=".yaml,.yml" onChange={(event) => void onFile(event)} />
        </label>
        {parsed && (
          <div className="ai-doc-import-preview">{t("portals.import")}<b>{parsed.articles.length}</b>{t("portals.articles_match_address_creates_new")}</div>
        )}
        {result && (
          <div className="ai-doc-import-report">
            <div className="ai-doc-import-summary">{t("ai.created")}<b>{result.created}</b>{t("ai.updated")}<b>{result.updated}</b>{t("ai.unchanged")}<b>{result.unchanged}</b>
            </div>
            {result.failed.length > 0 && (
              <ul className="ai-doc-import-failed">
                {result.failed.map((item, index) => (
                  <li key={index}>{item.slug ? `«${item.slug}»: ` : ""}{item.detail}</li>
                ))}
              </ul>
            )}
          </div>
        )}
        {error && <div className="ai-doc-error">{error}</div>}
        <div className="integration-form-actions">
          <Button variant="secondary" disabled={busy} onClick={onClose}>{t("common.close")}</Button>
          <Button variant="primary" icon="download" disabled={!parsed || busy} onClick={submit}>
            {busy ? t("portals.importing") : t("portals.import_2")}
          </Button>
        </div>
      </div>
    </Modal>
  );
}

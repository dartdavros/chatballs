import { useEffect, useMemo, useRef, useState } from "react";

import { Icon } from "../../../shared/icons";
import { LoadingState } from "../../../shared/ui";
import { Button } from "../../../shared/ui-controls";
import { pluralRu } from "../../../shared/utils";
import type { RouteKey } from "../../../types";
import { downloadKnowledgeTemplate } from "./downloadKnowledgeTemplate";
import { parseKnowledgeYaml, type ParsedKnowledgeYaml } from "./parseKnowledgeYaml";
import {
  fetchKnowledgeCategories,
  fetchKnowledgeList,
  importKnowledge,
  type KnowledgeCategory,
  type KnowledgeImportReport,
  type KnowledgeItem,
} from "./model";

// Импорт YAML (дизайн-базлайн v2, кадр KB8): файл разбирается до применения —
// видно, что создастся, что обновится и где ошибка пути. Импорт не создаёт
// категории неявно, поэтому несуществующий categoryPath отклоняется отдельно.

type ImportAction = "create" | "update" | "error";

type ImportRow = {
  document: ParsedKnowledgeYaml["documents"][number];
  action: ImportAction;
  path: string;
  note: string;
};

const ACTION_LABEL: Record<ImportAction, string> = {
  create: "создать",
  update: "обновить",
  error: "ошибка",
};

/** Разрешает путь категории в дерево организации: путь ищется по уровням. */
function resolvePath(categories: KnowledgeCategory[], path: string[]): { ok: boolean; missing: string } {
  let parentId: number | null = null;
  for (const name of path) {
    const found: KnowledgeCategory | undefined = categories.find(
      (category) => category.parentId === parentId && category.name === name,
    );
    if (!found) return { ok: false, missing: name };
    parentId = found.id;
  }
  return { ok: true, missing: "" };
}

function planRows(
  parsed: ParsedKnowledgeYaml,
  categories: KnowledgeCategory[],
  items: KnowledgeItem[],
): ImportRow[] {
  const byTitle = new Map(items.map((item) => [item.title, item]));
  return parsed.documents.map((document) => {
    const existing = byTitle.get(document.title) ?? null;
    if (document.categoryPath) {
      const { ok, missing } = resolvePath(categories, document.categoryPath);
      if (!ok) {
        return {
          document,
          action: "error",
          path: document.categoryPath.join(" / "),
          note: `категории «${missing}» нет — импорт не создаёт категории. Создайте её или уберите последний уровень пути.`,
        };
      }
    }
    const path = document.categoryPath ? document.categoryPath.join(" / ") : "не указана";
    if (!existing) {
      return {
        document,
        action: "create",
        path,
        note: document.categoryPath ? "" : "попадёт в «Без категории»",
      };
    }
    const samePlace = document.categoryPath
      && document.categoryPath[document.categoryPath.length - 1] === existing.category.name;
    return {
      document,
      action: "update",
      path,
      note: samePlace
        ? "категория в файле совпадает с текущей"
        : "совпал заголовок — заменим текст и пересоберём фрагменты",
    };
  });
}

/** «42 КБ» — размер выбранного файла в карточке. */
function fileSize(size: number): string {
  const kilobytes = size / 1024;
  return kilobytes >= 1024
    ? `${(kilobytes / 1024).toLocaleString("ru-RU", { maximumFractionDigits: 1 })} МБ`
    : `${Math.max(1, Math.round(kilobytes)).toLocaleString("ru-RU")} КБ`;
}

export function KnowledgeImportPage({
  canManage,
  setRoute,
}: {
  canManage: boolean;
  setRoute: (route: RouteKey) => void;
}) {
  const [categories, setCategories] = useState<KnowledgeCategory[]>([]);
  const [items, setItems] = useState<KnowledgeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [file, setFile] = useState<File | null>(null);
  const [parsed, setParsed] = useState<ParsedKnowledgeYaml | null>(null);
  const [report, setReport] = useState<KnowledgeImportReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    Promise.all([fetchKnowledgeCategories(), fetchKnowledgeList()])
      .then(([categoryPayload, itemPayload]) => {
        setCategories(categoryPayload.items);
        setItems(itemPayload.items);
      })
      .catch(() => setError("Не удалось загрузить категории и знания"))
      .finally(() => setLoading(false));
  }, []);

  const rows = useMemo(
    () => (parsed ? planRows(parsed, categories, items) : []),
    [categories, items, parsed],
  );
  const counts = {
    create: rows.filter((row) => row.action === "create").length,
    update: rows.filter((row) => row.action === "update").length,
    error: rows.filter((row) => row.action === "error").length,
  };
  const importable = rows.filter((row) => row.action !== "error");

  async function pick(selected: File) {
    setError("");
    setReport(null);
    setFile(selected);
    try {
      setParsed(parseKnowledgeYaml(await selected.text()));
    } catch (caught) {
      setParsed(null);
      setError(caught instanceof Error ? caught.message : "Не удалось прочитать файл");
    }
  }

  async function submit() {
    if (importable.length === 0) return;
    setBusy(true);
    setError("");
    try {
      setReport(await importKnowledge(importable.map((row) => row.document)));
      setParsed(null);
      setFile(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось импортировать");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="knowledge-card">
      <div className="knowledge-card-head is-plain">
        <nav className="knowledge-breadcrumbs">
          <button className="link is-strong" type="button" onClick={() => setRoute("knowledge")}>База знаний</button>
          <span><span className="knowledge-crumb-sep">/</span><b>Импорт YAML</b></span>
        </nav>
        <h2>Импорт материалов</h2>
        <p>Файл разбирается до применения: видно, что создастся, что обновится и где ошибка.</p>
      </div>

      <div className="knowledge-plain-body">
        <div className="knowledge-import-layout">
          <input
            ref={fileInputRef}
            hidden
            accept=".yaml,.yml"
            type="file"
            onChange={(event) => {
              const selected = event.target.files?.[0];
              event.target.value = "";
              if (selected) void pick(selected);
            }}
          />

          <div className="knowledge-import-file">
            <i><Icon name="file" size={19} strokeWidth={1.8} /></i>
            <span>
              <strong>{file ? file.name : "Файл не выбран"}</strong>
              <small>
                {file && parsed
                  ? `${fileSize(file.size)} · ${pluralRu(parsed.documents.length, ["документ", "документа", "документов"])} · разобран без ошибок формата`
                  : file
                    ? `${fileSize(file.size)} · файл не разобран`
                    : "YAML вида documents: [{ title, description?, content, categoryPath? }]"}
              </small>
            </span>
            <button type="button" onClick={() => fileInputRef.current?.click()}>
              {file ? "Выбрать другой файл" : "Выбрать файл"}
            </button>
            <button className="knowledge-import-template" type="button" onClick={downloadKnowledgeTemplate}>
              <Icon name="download" size={14} strokeWidth={1.9} />Шаблон
            </button>
          </div>

          {error && <div className="knowledge-form-error">{error}</div>}

          {loading && <LoadingState variant="inline" />}

          {report && (
            <div className="knowledge-import-report">
              <strong>Импорт завершён</strong>
              <span>
                Создано: <b>{report.created}</b> · Обновлено: <b>{report.updated}</b> · Без изменений: <b>{report.unchanged}</b>
              </span>
              {report.failed.length > 0 && (
                <ul>
                  {report.failed.map((failure, index) => (
                    <li key={index}>{failure.title ? `«${failure.title}»: ` : ""}{failure.detail}</li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {parsed && (
            <div className="knowledge-import-plan">
              <div className="knowledge-import-plan-head">
                <strong>Что произойдёт</strong>
                <span>
                  {counts.create > 0 && <small className="is-create">создать {counts.create}</small>}
                  {counts.update > 0 && <small className="is-update">обновить {counts.update}</small>}
                  {counts.error > 0 && <small className="is-error">ошибка {counts.error}</small>}
                </span>
              </div>
              <table className="knowledge-import-table">
                <thead>
                  <tr>
                    <th>ДОКУМЕНТ</th>
                    <th>CATEGORYPATH</th>
                    <th>ДЕЙСТВИЕ</th>
                    <th>ЗАМЕЧАНИЕ</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, index) => (
                    <tr className={row.action === "error" ? "is-error" : ""} key={`${row.document.title}-${index}`}>
                      <td><code>{row.document.title}</code></td>
                      <td className="knowledge-import-path">{row.path}</td>
                      <td><span className={`knowledge-import-action is-${row.action}`}>{ACTION_LABEL[row.action]}</span></td>
                      <td className="knowledge-import-note">{row.note}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {parsed && (
            <div className="knowledge-import-actions">
              <span>
                Импорт не создаёт категории неявно: документ с несуществующим <code>categoryPath</code>{" "}
                отклоняется отдельно, остальные применяются. Без указания пути документ попадает в
                «Без категории».
              </span>
              <Button variant="secondary" disabled={busy} onClick={() => setRoute("knowledge")}>Отмена</Button>
              <Button variant="primary" disabled={busy || !canManage || importable.length === 0} onClick={() => void submit()}>
                Импортировать {pluralRu(importable.length, ["документ", "документа", "документов"])}
              </Button>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

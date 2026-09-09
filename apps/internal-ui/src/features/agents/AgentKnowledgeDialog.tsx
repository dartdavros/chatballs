import { Modal } from "antd";
import { useEffect, useMemo, useState } from "react";

import { Icon } from "../../shared/icons";
import { LoadingState } from "../../shared/ui";
import { Button, SearchInput } from "../../shared/ui-controls";
import { shortDate } from "../../shared/utils";
import { fetchKnowledgeList } from "../ai/knowledge/api";
import { listPortalArticles, listSupportPortals } from "../support-portals/api";
import type { AgentCard } from "./model";
import { t } from "../../i18n";

// «Выбрать» в блоке «Знания» карточки агента (кадры G3/G5): один список из
// материалов библиотеки и опубликованных статей порталов. Агент отвечает
// только по явно выбранным знаниям (ADR-CHATBALLS-0041 §8).

type Choice = {
  key: string;
  kind: "knowledge" | "article";
  id: number;
  title: string;
  icon: "doc" | "globe";
  meta: string;
  disabled: boolean;
};

export function AgentKnowledgeDialog({ card, onClose, onSave }: {
  card: AgentCard;
  onClose: () => void;
  onSave: (selection: { knowledgeIds: number[]; articleIds: number[] }) => Promise<void>;
}) {
  const [choices, setChoices] = useState<Choice[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [search, setSearch] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [picked, setPicked] = useState<Set<string>>(
    () => new Set([
      ...card.knowledge.map((item) => `k${item.id}`),
      ...card.portalArticles.map((article) => `a${article.id}`),
    ]),
  );

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const library = await fetchKnowledgeList();
        const portals = await listSupportPortals();
        const articleLists = await Promise.all(portals.items.map((portal) => listPortalArticles(portal.id)));
        if (cancelled) return;
        const articles: Choice[] = portals.items.flatMap((portal, index) => articleLists[index].items
          .filter((article) => article.status === "PUBLISHED")
          .map((article) => ({
            key: `a${article.id}`,
            kind: "article" as const,
            id: article.id,
            title: article.publishedRevision?.title ?? article.slug,
            icon: "globe" as const,
            meta: t("ai.portal_named", { name: portal.name }),
            disabled: false,
          })));
        setChoices([
          ...library.items.map((item): Choice => ({
            key: `k${item.id}`,
            kind: "knowledge",
            id: item.id,
            title: item.title,
            icon: "doc",
            meta: item.isEnabled ? t("ai.updated_on", { date: shortDate(item.updatedAt) }) : t("common.off"),
            disabled: false,
          })),
          ...articles,
        ]);
      } catch {
        if (!cancelled) setFailed(true);
      }
    }
    void load();
    return () => { cancelled = true; };
  }, []);

  const visible = useMemo(() => {
    const needle = search.trim().toLowerCase();
    if (!needle || choices === null) return choices ?? [];
    return choices.filter((choice) => choice.title.toLowerCase().includes(needle));
  }, [choices, search]);

  function toggle(key: string) {
    setPicked((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  async function submit() {
    if (choices === null) return;
    setSaving(true);
    setError("");
    try {
      await onSave({
        knowledgeIds: choices.filter((choice) => choice.kind === "knowledge" && picked.has(choice.key)).map((choice) => choice.id),
        articleIds: choices.filter((choice) => choice.kind === "article" && picked.has(choice.key)).map((choice) => choice.id),
      });
      onClose();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : t("ai.could_not_save_selection"));
      setSaving(false);
    }
  }

  return (
    <Modal className="agent-knowledge-modal" open width={560} title={t("ai.select_knowledge")} onCancel={onClose} footer={null} destroyOnClose>
      <p className="agent-create-lead">{t("ai.agent_answers_only_from_selected")}</p>
      <SearchInput className="agent-knowledge-search" placeholder={t("ai.search_by_title")} value={search} onChange={setSearch} />
      {choices === null && !failed && <LoadingState />}
      {failed && <div className="agent-form-error">{t("ai.could_not_load_material_list")}</div>}
      {choices !== null && (
        <div className="agent-knowledge-choices">
          {visible.length === 0 && <p className="agent-knowledge-nothing">{t("common.nothing_found")}</p>}
          {visible.map((choice) => (
            <label className={`agent-knowledge-choice ${picked.has(choice.key) ? "is-picked" : ""}`} key={choice.key}>
              <input type="checkbox" checked={picked.has(choice.key)} onChange={() => toggle(choice.key)} />
              <Icon name={choice.icon} size={15} strokeWidth={1.9} />
              <strong>{choice.title}</strong>
              <small>{choice.meta}</small>
            </label>
          ))}
        </div>
      )}
      {error && <div className="agent-form-error">{error}</div>}
      <div className="agent-create-actions">
        <Button variant="secondary" onClick={onClose}>{t("common.cancel")}</Button>
        <Button variant="primary" disabled={choices === null || saving} onClick={() => void submit()}>
          {saving ? t("ai.saving") : t("common.save")}
        </Button>
      </div>
    </Modal>
  );
}

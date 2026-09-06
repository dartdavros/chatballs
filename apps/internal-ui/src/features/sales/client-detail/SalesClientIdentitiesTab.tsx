import { useState } from "react";

import { ChannelGlyph } from "../../../shared/badges";
import { ContactAvatar } from "../../conversations/ContactAvatar";
import { Button } from "../../../shared/ui-controls";
import { EmptyState } from "../../../shared/ui";
import { SalesClientMergeDialog, SalesClientUnmergeDialog } from "./SalesClientMergeDialog";
import type { ClientDetailVm } from "./model";

// Вкладка «Идентификаторы» (кадр K5): идентичности по подключениям и, справа,
// предложение объединения. Объединять и разъединять может только владелец
// (ADR-HUB-0006) — оператор и админ видят предложение и открывают сравнение.

export function SalesClientIdentitiesTab({ client, canMerge, openClient, onMerge, onUnmerge }: {
  client: ClientDetailVm;
  canMerge: boolean;
  openClient: (id: number) => void;
  onMerge: (sourceId: number, reason: string) => Promise<void>;
  onUnmerge: (mergeId: number, reason: string) => Promise<void>;
}) {
  const [merging, setMerging] = useState(false);
  const [reverting, setReverting] = useState<ClientDetailVm["merges"][number] | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function run(action: () => Promise<void>, done: () => void) {
    setSaving(true);
    setError("");
    try {
      await action();
      done();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось выполнить операцию");
    } finally {
      setSaving(false);
    }
  }

  if (client.identities.length === 0 && client.merges.length === 0) {
    return <EmptyState title="Нет идентификаторов подключений" />;
  }

  const rail = client.duplicate || client.merges.length > 0;
  return (
    <div className={`sales-client-ids ${rail ? "" : "is-single"}`}>
      <div className="sales-client-ids-card">
        {client.identities.map((identity) => (
          <div className="sales-client-identity-row" key={`${identity.name}-${identity.value}`}>
            <span className="sales-client-identity-tile" style={{ background: identity.bg, color: identity.color }}>
              <ChannelGlyph provider={identity.code ?? ""} size={18} />
            </span>
            <span className="sales-client-identity-main">
              <strong>{identity.name}</strong>
              <small>{identity.value}</small>
            </span>
            <small className="sales-client-identity-since">{identity.since}</small>
            <b className={identity.confirmed ? "is-ok" : ""}>{identity.status}</b>
          </div>
        ))}
        <p>Идентичности разных подключений не объединяются автоматически (ADR-0006). Подтверждённой считается только та, что подключение отдало с проверенным телефоном.</p>
      </div>
      {rail && (
        <div className="sales-client-ids-rail">
          {client.duplicate && (
            <section className="sales-client-section-card sales-client-duplicate">
              <div className="sales-client-duplicate-head">
                <h3>Возможный дубликат</h3>
                <b>предложение</b>
              </div>
              <p>Совпадает телефон{client.duplicate.phoneVerified ? ", подтверждённый подключением" : " (не подтверждён подключением)"}. Объединение перенесёт идентичности и диалоги; операция аудируется и требует причины.</p>
              <div className="sales-client-duplicate-row">
                <ContactAvatar avatarUrl={client.duplicate.avatarUrl || undefined} initials={client.duplicate.initials} background="var(--n-4)" className="sales-client-duplicate-avatar" />
                <span>
                  <strong>{client.duplicate.name} · {client.duplicate.cid}</strong>
                  <small>{client.duplicate.sourceLabel}</small>
                </span>
              </div>
              <div className="sales-client-duplicate-actions">
                {canMerge
                  ? <Button variant="primary" onClick={() => { setError(""); setMerging(true); }}>Сравнить и объединить</Button>
                  : <Button variant="primary" onClick={() => openClient(client.duplicate!.id)}>Открыть и сравнить</Button>}
                <Button variant="secondary" onClick={() => openClient(client.duplicate!.id)}>Не то</Button>
              </div>
              {!canMerge && <small className="sales-client-duplicate-note">Объединять контакты может только владелец (ADR-0006).</small>}
            </section>
          )}
          {client.merges.length > 0 && (
            <section className="sales-client-section-card">
              <h3>Объединённые контакты</h3>
              {client.merges.map((merge) => (
                <div className="sales-client-merge-row" key={merge.id}>
                  <div>
                    <strong>{merge.sourceName} · {merge.sourceCid}</strong>
                    <small>{merge.identities} идентичн. · {merge.conversations} диал. · {merge.actor || "система"} · {merge.atLabel}</small>
                    <em>{merge.reason}</em>
                  </div>
                  {canMerge && (
                    <button type="button" onClick={() => { setError(""); setReverting(merge); }}>Разъединить</button>
                  )}
                </div>
              ))}
            </section>
          )}
        </div>
      )}
      {client.duplicate && (
        <SalesClientMergeDialog
          client={client}
          open={merging}
          saving={saving}
          error={error}
          onClose={() => setMerging(false)}
          onMerge={(reason) => void run(() => onMerge(client.duplicate!.id, reason), () => setMerging(false))}
        />
      )}
      <SalesClientUnmergeDialog
        merge={reverting}
        open={Boolean(reverting)}
        saving={saving}
        error={error}
        onClose={() => setReverting(null)}
        onRevert={(reason) => void run(() => onUnmerge(reverting!.id, reason), () => setReverting(null))}
      />
    </div>
  );
}

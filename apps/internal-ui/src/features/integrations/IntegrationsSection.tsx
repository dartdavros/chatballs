import { Modal } from "antd";
import { useCallback, useEffect, useState } from "react";

import { api } from "../../api/client";
import { EmptyState, LoadingState } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
import { ConnectionsTable } from "./ConnectionsTable";
import { IntegrationForm } from "./IntegrationForm";
import type { Integration, IntegrationKind } from "./model";
import { ProvidersTable } from "./ProvidersTable";

// Секция интеграций одного рода — блок экрана «Настройки» (SPEC-HUB-0031
// §8.6): подключения (MESSENGER) и AI-провайдеры (LLM_PROVIDER) — отдельные
// вертикальные секции, отдельный раздел «Интеграции» упразднён.

export function IntegrationsSection({ kind }: { kind: IntegrationKind }) {
  const [items, setItems] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [form, setForm] = useState<{ initial: Integration | null } | null>(null);
  const [testingId, setTestingId] = useState<number | null>(null);
  const [deleting, setDeleting] = useState<Integration | null>(null);
  const [deletingError, setDeletingError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const payload = await api<{ items: Integration[] }>("/api/v1/integrations/");
      setItems(payload.items.filter((item) => item.kind === kind));
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [kind]);

  useEffect(() => {
    void load();
  }, [load]);

  async function test(integration: Integration) {
    setTestingId(integration.id);
    try {
      const payload = await api<{ integration: Integration }>(`/api/v1/integrations/${integration.id}/test/`, { method: "POST" });
      setItems((current) => current.map((item) => (item.id === integration.id ? payload.integration : item)));
    } catch {
      void load();
    } finally {
      setTestingId(null);
    }
  }

  async function toggleActive(integration: Integration) {
    try {
      const payload = await api<{ integration: Integration }>(`/api/v1/integrations/${integration.id}/`, {
        method: "PATCH",
        body: JSON.stringify({ isActive: !integration.isActive }),
      });
      setItems((current) => current.map((item) => (
        item.id === integration.id ? payload.integration : item
      )));
    } catch {
      void load();
    }
  }

  async function confirmDelete() {
    if (!deleting) return;
    try {
      await api(`/api/v1/integrations/${deleting.id}/`, { method: "DELETE" });
      setDeleting(null);
      void load();
    } catch (caught) {
      setDeletingError(caught instanceof Error ? caught.message : "Не удалось удалить");
    }
  }

  const isConnections = kind === "MESSENGER";
  const rowHandlers = {
    testingId,
    onTest: test,
    onEdit: (item: Integration) => setForm({ initial: item }),
    onToggleActive: toggleActive,
    onDelete: (item: Integration) => { setDeletingError(null); setDeleting(item); },
  };

  if (loading) return <LoadingState />;
  if (error) return <EmptyState title="Не удалось загрузить интеграции" />;

  return (
    <div className="integrations-section">
      <div className="integrations-section-actions">
        <Button variant="primary" icon="plus" onClick={() => setForm({ initial: null })}>
          {isConnections ? "Добавить подключение" : "Добавить провайдера"}
        </Button>
      </div>
      {items.length === 0 ? (
        <EmptyState title={isConnections ? "Подключений пока нет. Добавьте бота, почту или Web-виджет." : "Провайдеров пока нет. Добавьте OpenRouter или Custom endpoint."} />
      ) : isConnections ? (
        <ConnectionsTable items={items} {...rowHandlers} />
      ) : (
        <ProvidersTable items={items} {...rowHandlers} />
      )}
      {form && (
        <IntegrationForm
          initial={form.initial}
          kind={kind}
          onClose={() => setForm(null)}
          onSaved={() => { setForm(null); void load(); }}
        />
      )}
      {deleting && (
        <Modal open title="Удалить интеграцию?" onCancel={() => setDeleting(null)} footer={null} destroyOnClose>
          <div className="integration-form">
            <p>{`«${deleting.name}» будет удалена. Действие необратимо.`}</p>
            {deletingError && <div className="integration-form-error">{deletingError}</div>}
            <div className="integration-form-actions">
              <Button variant="secondary" onClick={() => setDeleting(null)}>Отмена</Button>
              <Button variant="danger-outline" onClick={() => void confirmDelete()}>Удалить</Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

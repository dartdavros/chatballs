import { Modal } from "antd";
import { useCallback, useEffect, useState } from "react";

import { api } from "../../api/client";
import { EmptyState, LoadingState, PageHeader } from "../../shared/ui";
import { Button, UnderlineTabs } from "../../shared/ui-controls";
import { ConnectionsTable } from "./ConnectionsTable";
import { IntegrationForm } from "./IntegrationForm";
import { KIND_LABEL, type Integration, type IntegrationKind } from "./model";
import { ProvidersTable } from "./ProvidersTable";

// Страница «Интеграции» (SPEC-HUB-0025 §2): два таба по родам — подключения
// (MESSENGER) и LLM-провайдеры; кнопка создания контекстна активному табу.
type FormState = { initial: Integration | null; kind: IntegrationKind } | null;

export function IntegrationsPage() {
  const [items, setItems] = useState<Integration[]>([]);
  const [tab, setTab] = useState<IntegrationKind>("MESSENGER");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [form, setForm] = useState<FormState>(null);
  const [testingId, setTestingId] = useState<number | null>(null);
  const [deleting, setDeleting] = useState<Integration | null>(null);
  const [deletingError, setDeletingError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const payload = await api<{ items: Integration[] }>("/api/v1/integrations/");
      setItems(payload.items);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

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

  function startDelete(integration: Integration) {
    setDeletingError(null);
    setDeleting(integration);
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

  const connections = items.filter((item) => item.kind === "MESSENGER");
  const providers = items.filter((item) => item.kind === "LLM_PROVIDER");
  const isConnections = tab === "MESSENGER";
  const shown = isConnections ? connections : providers;
  const rowHandlers = {
    testingId,
    onTest: test,
    onEdit: (item: Integration) => setForm({ initial: item, kind: item.kind }),
    onToggleActive: toggleActive,
    onDelete: startDelete,
  };

  const header = (
    <PageHeader
      title="Интеграции"
      text="Подключения мессенджеров, почты и LLM-провайдеры · заводятся и проверяются здесь"
      action={
        <Button variant="primary" icon="plus" onClick={() => setForm({ initial: null, kind: tab })}>
          {isConnections ? "Добавить подключение" : "Добавить провайдера"}
        </Button>
      }
    />
  );

  if (loading) return <div className="integrations-page">{header}<LoadingState /></div>;
  if (error) return <div className="integrations-page">{header}<EmptyState title="Не удалось загрузить интеграции" /></div>;

  return (
    <div className="integrations-page">
      {header}
      <UnderlineTabs
        className="integrations-tabs"
        items={[
          { key: "MESSENGER", label: KIND_LABEL.MESSENGER, count: connections.length },
          { key: "LLM_PROVIDER", label: KIND_LABEL.LLM_PROVIDER, count: providers.length },
        ]}
        value={tab}
        onChange={setTab}
      />
      {shown.length === 0 ? (
        <EmptyState title={isConnections ? "Подключений пока нет. Добавьте бота, почту или Web-виджет." : "Провайдеров пока нет. Добавьте OpenRouter или Custom endpoint."} />
      ) : isConnections ? (
        <ConnectionsTable items={connections} {...rowHandlers} />
      ) : (
        <ProvidersTable items={providers} {...rowHandlers} />
      )}
      {form && (
        <IntegrationForm
          initial={form.initial}
          kind={form.kind}
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

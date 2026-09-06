import { Modal } from "antd";
import { useState } from "react";

import { api } from "../../api/client";
import { EmptyState } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
import { ConnectionsTable } from "./ConnectionsTable";
import type { Integration, IntegrationKind } from "./model";
import { ProvidersTable } from "./ProvidersTable";

// Таблица интеграций одного рода — раздел экрана «Настройки» (дизайн-базлайн v2,
// кадры N3/N4): подключения (MESSENGER) и AI-провайдеры (LLM_PROVIDER) — два
// раздела субменю. Список грузит страница настроек (счётчики в субменю), форма
// создания открывается primary-кнопкой в шапке раздела.

export function IntegrationsSection({ kind, items, reload, onEdit }: {
  kind: IntegrationKind;
  items: Integration[];
  reload: () => void;
  onEdit: (integration: Integration) => void;
}) {
  const [testingId, setTestingId] = useState<number | null>(null);
  const [deleting, setDeleting] = useState<Integration | null>(null);
  const [deletingError, setDeletingError] = useState<string | null>(null);

  async function test(integration: Integration) {
    setTestingId(integration.id);
    try {
      await api(`/api/v1/integrations/${integration.id}/test/`, { method: "POST" });
    } catch {
      /* статус придёт из перезагрузки списка */
    } finally {
      setTestingId(null);
      reload();
    }
  }

  async function toggleActive(integration: Integration) {
    try {
      await api(`/api/v1/integrations/${integration.id}/`, {
        method: "PATCH",
        body: JSON.stringify({ isActive: !integration.isActive }),
      });
    } finally {
      reload();
    }
  }

  async function confirmDelete() {
    if (!deleting) return;
    try {
      await api(`/api/v1/integrations/${deleting.id}/`, { method: "DELETE" });
      setDeleting(null);
      reload();
    } catch (caught) {
      setDeletingError(caught instanceof Error ? caught.message : "Не удалось удалить");
    }
  }

  const isConnections = kind === "MESSENGER";
  const rowHandlers = {
    testingId,
    onTest: test,
    onEdit,
    onToggleActive: toggleActive,
    onDelete: (item: Integration) => { setDeletingError(null); setDeleting(item); },
  };

  return (
    <div className="integrations-section">
      {items.length === 0 ? (
        <EmptyState title={isConnections ? "Подключений пока нет. Добавьте бота, почту или Web-виджет." : "Провайдеров пока нет. Добавьте OpenRouter или Custom endpoint."} />
      ) : isConnections ? (
        <ConnectionsTable items={items} {...rowHandlers} />
      ) : (
        <ProvidersTable items={items} {...rowHandlers} />
      )}
      {isConnections && items.length > 0 && (
        <p className="settings-section-note">Код вставки Web-виджета копируется на карточке его агента.</p>
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

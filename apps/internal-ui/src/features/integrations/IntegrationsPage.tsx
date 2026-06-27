import { Dropdown, Modal } from "antd";
import { useCallback, useEffect, useState } from "react";

import { api } from "../../api/client";
import { Icon } from "../../shared/icons";
import { EmptyState, LoadingState, PageHeader } from "../../shared/ui";
import { Button, ToneBadge } from "../../shared/ui-controls";
import { IntegrationForm } from "./IntegrationForm";
import { KIND_LABEL, PROVIDERS, STATUS_META, type Integration, type IntegrationKind } from "./model";

const KIND_ORDER: IntegrationKind[] = ["LLM_PROVIDER", "MESSENGER"];

function formatChecked(value: string | null): string {
  if (!value) return "ещё не проверялось";
  return new Date(value).toLocaleString("ru-RU", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

export function IntegrationsPage() {
  const [items, setItems] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [form, setForm] = useState<Integration | "new" | null>(null);
  const [testingId, setTestingId] = useState<number | null>(null);
  const [menuId, setMenuId] = useState<number | null>(null);

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

  function confirmDelete(integration: Integration) {
    setMenuId(null);
    Modal.confirm({
      title: "Удалить интеграцию?",
      content: `«${integration.name}» будет удалена. Действие необратимо.`,
      okText: "Удалить",
      okButtonProps: { danger: true },
      cancelText: "Отмена",
      onOk: async () => {
        await api(`/api/v1/integrations/${integration.id}/`, { method: "DELETE" });
        void load();
      },
    });
  }

  const header = (
    <PageHeader
      title="Интеграции"
      text="Провайдеры (LLM) и подключения (боты/виджеты) · заводятся и проверяются здесь"
      action={<Button variant="primary" icon="plus" onClick={() => setForm("new")}>Создать интеграцию</Button>}
    />
  );

  if (loading) return <div className="integrations-page">{header}<LoadingState /></div>;
  if (error) return <div className="integrations-page">{header}<EmptyState title="Не удалось загрузить интеграции" /></div>;

  return (
    <div className="integrations-page">
      {header}
      {items.length === 0 ? (
        <EmptyState title="Пока нет интеграций. Создайте OpenRouter и MAX-подключение." />
      ) : (
        KIND_ORDER.map((kind) => {
          const group = items.filter((item) => item.kind === kind);
          if (group.length === 0) return null;
          return (
            <section className="integration-group" key={kind}>
              <h2>{KIND_LABEL[kind]}</h2>
              <div className="table-card">
                <table className="baseline-table">
                  <thead>
                    <tr>
                      <th>НАЗВАНИЕ</th>
                      <th>СЕКРЕТ</th>
                      <th>КОНФИГ</th>
                      <th>СТАТУС</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {group.map((item) => {
                      const meta = PROVIDERS[item.provider];
                      const status = STATUS_META[item.status];
                      const menuItems = [
                        { key: "edit", label: <button type="button" onClick={() => { setMenuId(null); setForm(item); }}><Icon name="edit" size={15} />Изменить</button> },
                        { type: "divider" as const },
                        { key: "delete", label: <button type="button" className="warning" onClick={() => confirmDelete(item)}><Icon name="trash" size={15} />Удалить</button> },
                      ];
                      return (
                        <tr key={item.id}>
                          <td>
                            <div className="product-cell">
                              <span className="product-icon"><Icon name={item.kind === "LLM_PROVIDER" ? "robot" : "plug"} size={20} /></span>
                              <span><strong>{item.name}</strong><small>{meta.label}{item.config.botUsername ? ` · ${item.config.botUsername}` : ""}</small></span>
                            </div>
                          </td>
                          <td>{item.hasSecret ? <code className="ai-mono">••••••••</code> : <span className="product-empty-value">—</span>}</td>
                          <td className="integration-config">
                            <span>{item.config.baseUrl || meta.defaultBaseUrl || "—"}</span>
                            {item.config.defaultModel && <small>{item.config.defaultModel}</small>}
                          </td>
                          <td>
                            <div className="integration-status">
                              <ToneBadge bg={status.bg} color={status.color}>{status.label}</ToneBadge>
                              <small>{item.status === "ERROR" && item.lastError ? item.lastError : formatChecked(item.lastCheckedAt)}</small>
                            </div>
                          </td>
                          <td className="row-actions">
                            <div className="ai-row-actions">
                              <Button variant="secondary" icon="refresh" iconSize={14} disabled={!meta.testable || testingId === item.id} onClick={() => test(item)}>
                                {testingId === item.id ? "Проверка…" : "Проверить"}
                              </Button>
                              <Dropdown
                                menu={{ items: menuItems }}
                                open={menuId === item.id}
                                onOpenChange={(open) => setMenuId(open ? item.id : null)}
                                trigger={["click"]}
                                overlayClassName="product-actions-dropdown"
                              >
                                <button className="row-menu-button" aria-label="Действия интеграции"><Icon name="more" /></button>
                              </Dropdown>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>
          );
        })
      )}
      {form && <IntegrationForm initial={form === "new" ? null : form} onClose={() => setForm(null)} onSaved={() => { setForm(null); void load(); }} />}
    </div>
  );
}

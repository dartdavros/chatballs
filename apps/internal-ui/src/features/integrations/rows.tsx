import { Dropdown } from "antd";
import { useState } from "react";

import { Icon, MaxLogo, TelegramLogo } from "../../shared/icons";
import { Button, ToneBadge } from "../../shared/ui-controls";
import { shortDateTime } from "../../shared/utils";
import { PROVIDERS, STATUS_META, type Integration, type IntegrationProvider } from "./model";

// Плитка подключения: фирменная марка на фирменном фоне (SPEC-CHATBALLS-0025 §2.3).
// Web использует глиф и цвет кнопки-лончера виджета (webchat/loader.py).
const TILE_CLASS: Partial<Record<IntegrationProvider, string>> = {
  TELEGRAM: "integration-tile--telegram",
  MAX: "integration-tile--max",
  WEB: "integration-tile--web",
  EMAIL: "integration-tile--email",
};

export function ConnectionIcon({ provider }: { provider: IntegrationProvider }) {
  const tile = TILE_CLASS[provider];
  // AI-провайдеры (кадр N3): знак «искры» на подложке цвета AI, у остальных —
  // нейтральная плитка.
  if (!tile) {
    return (
      <span className={`product-icon integration-tile ${provider === "OPENROUTER" ? "integration-tile--ai" : "integration-tile--neutral"}`}>
        <Icon name="sparkles" size={20} strokeWidth={1.9} />
      </span>
    );
  }
  return (
    <span className={`product-icon integration-tile ${tile}`}>
      {provider === "TELEGRAM" && <TelegramLogo size={20} />}
      {provider === "MAX" && <MaxLogo size={20} />}
      {provider === "WEB" && <Icon name="message" size={20} strokeWidth={1.9} />}
      {provider === "EMAIL" && <Icon name="mail" size={20} strokeWidth={1.9} />}
    </span>
  );
}

export function formatChecked(value: string | null): string {
  if (!value) return "ещё не проверялось";
  return shortDateTime(value);
}

export function StatusCell({ integration }: { integration: Integration }) {
  if (!integration.isActive) {
    return (
      <div className="integration-status">
        <ToneBadge bg="#f5f5f5" color="#8c8c8c">Отключено</ToneBadge>
        <small>Приём и отправка сообщений остановлены</small>
      </div>
    );
  }
  const status = STATUS_META[integration.status];
  return (
    <div className="integration-status">
      <ToneBadge bg={status.bg} color={status.color}>{status.label}</ToneBadge>
      <small>{integration.status === "ERROR" && integration.lastError ? integration.lastError : formatChecked(integration.lastCheckedAt)}</small>
    </div>
  );
}

type RowActionsProps = {
  integration: Integration;
  testing: boolean;
  onTest: (integration: Integration) => void;
  onEdit: (integration: Integration) => void;
  onToggleActive: (integration: Integration) => void;
  onDelete: (integration: Integration) => void;
};

export function RowActions({ integration, testing, onTest, onEdit, onToggleActive, onDelete }: RowActionsProps) {
  const [open, setOpen] = useState(false);
  const meta = PROVIDERS[integration.provider];
  const menuItems = [
    { key: "edit", label: <button type="button" onClick={() => { setOpen(false); onEdit(integration); }}><Icon name="edit" size={15} />Изменить</button> },
    ...(integration.kind === "MESSENGER" ? [{
      key: "active",
      label: (
        <button type="button" onClick={() => { setOpen(false); onToggleActive(integration); }}>
          <Icon name={integration.isActive ? "pause" : "plug"} size={15} />
          {integration.isActive ? "Отключить" : "Включить"}
        </button>
      ),
    }] : []),
    { type: "divider" as const },
    { key: "delete", label: <button type="button" className="warning" onClick={() => { setOpen(false); onDelete(integration); }}><Icon name="trash" size={15} />Удалить</button> },
  ];
  return (
    <div className="ai-row-actions">
      <Button variant="secondary" icon="refresh" iconSize={13} disabled={!meta.checkable || testing} onClick={() => onTest(integration)}>
        {testing ? "Проверка…" : "Проверить"}
      </Button>
      <Dropdown menu={{ items: menuItems }} open={open} onOpenChange={setOpen} trigger={["click"]} overlayClassName="app-dropdown">
        <button className="row-menu-button" type="button" aria-label="Действия интеграции"><Icon name="more" /></button>
      </Dropdown>
    </div>
  );
}

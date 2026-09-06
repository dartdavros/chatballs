import { useState, type ReactNode } from "react";

import { isManager } from "../../auth/access";
import type { EmployeeGroup, RouteKey, SessionUser } from "../../types";
import { OrganizationSettingsForm } from "../administration/OrganizationSettingsForm";
import { canManageSettings } from "../administration/model";
import { useAdministration } from "../administration/useAdministration";
import { IntegrationForm } from "../integrations/IntegrationForm";
import { IntegrationsSection } from "../integrations/IntegrationsSection";
import type { Integration, IntegrationKind } from "../integrations/model";
import { EmptyState, LoadingState } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
import { Icon } from "../../shared/icons";
import { useMediaQuery } from "../../shared/useMediaQuery";
import { DemoDataCard } from "./DemoDataCard";
import { CommunicationSettingsCard } from "./CommunicationSettingsCard";
import { StorageSettingsCard } from "./StorageSettingsCard";
import { GroupsSettingsCard } from "./GroupsSettingsCard";
import { DEFAULT_SETTINGS_SECTION, SETTINGS_SECTIONS, type SettingsSectionKey } from "./sections";
import { useIntegrations } from "./useIntegrations";

// «Настройки» (дизайн-базлайн v2, кадры N1–N7): субменю разделов 240px и один
// раздел на экране; ниже субменю — переходы на отдельные экраны «База знаний» и
// «Аудит действий». Профиль пользователя сюда не входит — это отдельная
// страница из меню пользователя. OWNER и ADMIN видят одно и то же (§3).

export function SettingsPage({ user, onUserUpdated, reload, groups = [], section, openSection, setRoute }: {
  user: SessionUser;
  onUserUpdated: (user: SessionUser) => void;
  reload: () => void;
  groups?: EmployeeGroup[];
  section: SettingsSectionKey | null;
  openSection: (section: SettingsSectionKey | null) => void;
  setRoute: (route: RouteKey) => void;
}) {
  const manager = isManager(user);
  const integrations = useIntegrations(manager);
  const [form, setForm] = useState<{ kind: IntegrationKind; initial: Integration | null } | null>(null);
  // Кадр M: на узком экране субменю и раздел — два отдельных экрана.
  const mobile = useMediaQuery("(max-width: 900px)");

  if (!manager) return <EmptyState title="Настройки доступны владельцу и администратору" />;

  const providers = integrations.items.filter((item) => item.kind === "LLM_PROVIDER");
  const connections = integrations.items.filter((item) => item.kind === "MESSENGER");
  const connectionsFailed = connections.some((item) => item.isActive && item.status === "ERROR");
  const counts: Partial<Record<SettingsSectionKey, number>> = {
    groups: groups.length,
    ai: providers.length,
    integrations: connections.length,
  };
  const active = section ?? (mobile ? null : DEFAULT_SETTINGS_SECTION);
  const current = SETTINGS_SECTIONS.find((item) => item.key === active) ?? null;

  const links = (
    <>
      <div className="settings-subnav-divider" />
      <div className="settings-subnav-caption">Отдельные экраны</div>
      <button className="settings-subnav-link" type="button" onClick={() => setRoute("aiKnowledge")}>
        <Icon name="folder" size={16} strokeWidth={1.9} /><span>База знаний</span><Icon name="external" size={13} strokeWidth={2} />
      </button>
      <button className="settings-subnav-link" type="button" onClick={() => setRoute("administrationAudit")}>
        <Icon name="list" size={16} strokeWidth={1.9} /><span>Аудит действий</span><Icon name="external" size={13} strokeWidth={2} />
      </button>
    </>
  );

  const subnav = (
    <nav className={`settings-subnav ${mobile && current ? "is-hidden" : ""}`}>
      <div className="settings-subnav-head"><h2>Настройки</h2></div>
      <div className="settings-subnav-list">
        {SETTINGS_SECTIONS.map((item) => (
          <button
            className={`settings-subnav-item ${item.key === active ? "is-active" : ""}`}
            key={item.key}
            type="button"
            onClick={() => openSection(item.key)}
          >
            <Icon name={item.icon} size={16} strokeWidth={1.9} />
            <span>{item.label}</span>
            {counts[item.key] !== undefined && counts[item.key]! > 0 && <small>{counts[item.key]}</small>}
            {item.key === "integrations" && connectionsFailed && item.key !== active && <i className="settings-subnav-warn" title="Есть ошибка" />}
            {/* Кадр M: на узком экране у пункта — шеврон перехода. */}
            <span className="settings-subnav-chevron"><Icon name="chevron" size={16} strokeWidth={2} /></span>
          </button>
        ))}
        {links}
      </div>
    </nav>
  );

  const headAction = current?.key === "ai"
    ? <Button variant="primary" icon="plus" onClick={() => setForm({ kind: "LLM_PROVIDER", initial: null })}>Добавить провайдера</Button>
    : current?.key === "integrations"
      ? <Button variant="primary" icon="plus" onClick={() => setForm({ kind: "MESSENGER", initial: null })}>Добавить подключение</Button>
      : null;

  return (
    <div className="settings-layout">
      {subnav}
      {current && (
        <section className={`settings-content ${mobile ? "is-single" : ""}`}>
          <div className={`settings-content-inner ${current.wide ? "is-wide" : ""}`}>
            <header className="settings-head">
              {mobile && (
                <button className="settings-head-back" type="button" aria-label="К списку разделов" onClick={() => openSection(null)}>
                  <Icon name="chevron" size={18} />
                </button>
              )}
              <div>
                <h2>{current.heading}</h2>
                <p>{current.lead}</p>
              </div>
              {headAction}
            </header>
            <SectionBody
              section={current.key}
              user={user}
              onUserUpdated={onUserUpdated}
              reload={reload}
              groups={groups}
              integrations={integrations}
              providers={providers}
              connections={connections}
              onEditIntegration={(item) => setForm({ kind: item.kind, initial: item })}
            />
          </div>
        </section>
      )}
      {form && (
        <IntegrationForm
          initial={form.initial}
          kind={form.kind}
          onClose={() => setForm(null)}
          onSaved={() => { setForm(null); integrations.reload(); }}
        />
      )}
    </div>
  );
}

function SectionBody({ section, user, onUserUpdated, reload, groups, integrations, providers, connections, onEditIntegration }: {
  section: SettingsSectionKey;
  user: SessionUser;
  onUserUpdated: (user: SessionUser) => void;
  reload: () => void;
  groups: EmployeeGroup[];
  integrations: ReturnType<typeof useIntegrations>;
  providers: Integration[];
  connections: Integration[];
  onEditIntegration: (integration: Integration) => void;
}): ReactNode {
  if (section === "organization") return <OrganizationSection user={user} onUserUpdated={onUserUpdated} />;
  if (section === "groups") return <GroupsSettingsCard groups={groups} reload={reload} />;
  if (section === "communication") return <CommunicationSettingsCard canManage={canManageSettings(user)} />;
  if (section === "storage") return <StorageSettingsCard canManage={canManageSettings(user)} />;
  if (section === "demo") return <DemoDataCard reload={reload} />;
  if (integrations.loading) return <LoadingState />;
  if (integrations.failed) return <EmptyState title="Не удалось загрузить интеграции" />;
  return (
    <IntegrationsSection
      kind={section === "ai" ? "LLM_PROVIDER" : "MESSENGER"}
      items={section === "ai" ? providers : connections}
      reload={integrations.reload}
      onEdit={onEditIntegration}
    />
  );
}

function OrganizationSection({ user, onUserUpdated }: { user: SessionUser; onUserUpdated: (user: SessionUser) => void }) {
  const page = useAdministration({ section: "organization", user, onUserUpdated });
  if (page.loading) return <LoadingState />;
  if (!page.organization) return <EmptyState title={page.error || "Не удалось загрузить настройки"} />;
  return (
    <OrganizationSettingsForm
      organization={page.organization}
      canManage={canManageSettings(user)}
      saving={page.saving}
      message={page.message}
      error={page.error}
      timezones={page.timezones}
      onChange={page.setOrganization}
      onSave={() => void page.save()}
      onUploadLogo={(file) => void page.uploadLogo(file)}
      onRemoveLogo={() => void page.removeLogo()}
    />
  );
}

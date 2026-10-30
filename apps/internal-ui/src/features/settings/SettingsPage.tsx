import { useState } from "react";

import { isManager } from "../../auth/access";
import type { EmployeeGroup, RouteKey, SessionUser } from "../../types";
import { IntegrationForm } from "../integrations/IntegrationForm";
import { AddIntegrationButton } from "../integrations/AddIntegrationButton";
import type { Integration, IntegrationKind } from "../integrations/model";
import { ServiceCardPage } from "../integrations/services/card/ServiceCardPage";
import { TAB_ROUTE, type IntegrationsTab, type IntegrationsView } from "../integrations/tabs";
import { EmptyState } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
import { Icon } from "../../shared/icons";
import { useMediaQuery } from "../../shared/useMediaQuery";
import { DEFAULT_SETTINGS_SECTION, visibleSettingsSections, type SettingsSectionKey } from "./sections";
import { SettingsSectionBody } from "./SettingsSectionBody";
import { RuleJournalCard } from "../handling-rules/RuleJournalCard";
import { useIntegrations } from "./useIntegrations";
import { useReplyTemplates } from "./useReplyTemplates";
import { useOnboarding } from "../onboarding/useOnboarding";
import type { TourTarget } from "../onboarding/steps";
import { t } from "../../i18n";

// Раздел «Настроек» как цель тура онбординга: имена совпадают с таблицей шагов.
const SECTION_TOUR_TARGET: Partial<Record<SettingsSectionKey, TourTarget>> = {
  ai: "settings-ai",
  integrations: "settings-integrations",
  platform: "settings-platform",
};

// «Настройки» (дизайн-базлайн v2, кадры N1–N7): субменю разделов 240px и один
// раздел на экране; ниже субменю — переходы на отдельные экраны «База знаний» и
// «Аудит действий». Профиль пользователя сюда не входит — это отдельная
// страница из меню пользователя. OWNER и ADMIN видят одно и то же (§3).
// «Платформа» кадра в базлайне не имеет — раздел собран по стандарту N6
// («Хранилище файлов»): заголовок карточки, поля, ряд действий.

export function SettingsPage({ user, onUserUpdated, reload, groups = [], section, openSection, openWebIntegration, openServiceConnection = () => undefined, integrationsView, setRoute, journal = false, openConversation }: {
  user: SessionUser;
  onUserUpdated: (user: SessionUser) => void;
  reload: () => void;
  groups?: EmployeeGroup[];
  section: SettingsSectionKey | null;
  openSection: (section: SettingsSectionKey | null) => void;
  openWebIntegration: (id: number) => void;
  openServiceConnection?: (id: number) => void;
  /** Вкладка «Интеграций» или карточка сервиса из адреса страницы. */
  integrationsView?: IntegrationsView;
  setRoute: (route: RouteKey) => void;
  journal?: boolean;
  openConversation: (id: number) => void;
}) {
  const manager = isManager(user);
  const integrations = useIntegrations(manager);
  const [form, setForm] = useState<{ kind: IntegrationKind; initial: Integration | null } | null>(null);
  const templates = useReplyTemplates(manager);
  // Кадр M: на узком экране субменю и раздел — два отдельных экрана.
  const mobile = useMediaQuery("(max-width: 900px)");
  const openScenario = (id: string) => {
    openSection("scenarios");
    const url = new URL(window.location.href); url.searchParams.set("scenario", id); window.history.replaceState(window.history.state, "", url);
  };

  if (!manager) return <EmptyState title={t("settings.settings_available_owner_administrators")} />;

  const providers = integrations.items.filter((item) => item.kind === "LLM_PROVIDER");
  const connections = integrations.items.filter((item) => item.kind !== "LLM_PROVIDER");
  const connectionsFailed = connections.some((item) => item.isActive && item.status === "ERROR");
  const counts: Partial<Record<SettingsSectionKey, number>> = {
    groups: groups.length,
    templates: templates.items.length,
    ai: providers.length,
    integrations: connections.length,
  };
  const active = journal ? "rules" : integrationsView ? "integrations" : section ?? (mobile ? null : DEFAULT_SETTINGS_SECTION);
  const integrationsTab = integrationsView?.tab ?? "entry";
  const openIntegrationsTab = (tab: IntegrationsTab) => tab === "entry" ? openSection("integrations") : setRoute(TAB_ROUTE[tab]);
  // Разделы про саму установку видит только её администратор.
  const sections = visibleSettingsSections(user);
  const onboarding = useOnboarding();
  const current = sections.find((item) => item.key === active) ?? null;

  const links = (
    <>
      <div className="settings-subnav-divider" />
      <div className="settings-subnav-caption">{t("settings.separate_screens")}</div>
      <button className="settings-subnav-link" type="button" onClick={() => setRoute("administrationAudit")}>
        <Icon name="list" size={16} strokeWidth={1.9} /><span>{t("settings.action_audit")}</span><Icon name="external" size={13} strokeWidth={2} />
      </button>
      {/* Возврат в онбординг: он открывается в любой момент, а не только при
          первом входе. */}
      {onboarding?.available && (
        <>
          <div className="settings-subnav-divider" />
          <button className="settings-subnav-onboarding" type="button" onClick={onboarding.open}>
            <Icon name="sparkles" size={16} strokeWidth={1.9} />
            <span>{t("onboarding.title")}</span>
            <small>{t("onboarding.progress_short", { done: onboarding.doneCount, total: onboarding.steps.length })}</small>
          </button>
          <p className="settings-subnav-onboarding-note">{t("onboarding.settings_hint")}</p>
        </>
      )}
    </>
  );

  const subnav = (
    <nav className={`settings-subnav ${mobile && current ? "is-hidden" : ""}`}>
      <div className="settings-subnav-head"><h2>{t("common.settings")}</h2></div>
      <div className="settings-subnav-list">
        {sections.map((item) => (
          <button
            className={`settings-subnav-item ${item.key === active ? "is-active" : ""}`}
            key={item.key}
            type="button"
            data-onboarding-target={SECTION_TOUR_TARGET[item.key]}
            onClick={() => openSection(item.key)}
          >
            <Icon name={item.icon} size={16} strokeWidth={1.9} />
            <span>{item.label}</span>
            {counts[item.key] !== undefined && counts[item.key]! > 0 && <small>{counts[item.key]}</small>}
            {item.key === "integrations" && connectionsFailed && item.key !== active && <i className="settings-subnav-warn" title={t("settings.there_error")} />}
            {/* Кадр M: на узком экране у пункта — шеврон перехода. */}
            <span className="settings-subnav-chevron"><Icon name="chevronRight" size={16} strokeWidth={2} /></span>
          </button>
        ))}
        {links}
      </div>
    </nav>
  );

  const headAction = current?.key === "ai"
    ? <Button variant="primary" icon="plus" onClick={() => setForm({ kind: "LLM_PROVIDER", initial: null })}>{t("settings.add_provider")}</Button>
    : current?.key === "integrations" && integrationsTab !== "services"
      ? <AddIntegrationButton onEntry={() => setForm({ kind: "MESSENGER", initial: null })} onServer={(kind) => setRoute(kind === "mcp" ? "mcpServerCreate" : "httpServerCreate")} />
      : null;

  return (
    <div className="settings-layout">
      {subnav}
      {current && (
        <section className={`settings-content ${mobile ? "is-single" : ""}`}>
          <div className="settings-content-inner">
            {journal && <button className="link is-muted has-icon" type="button" onClick={() => openSection("rules")}><Icon name="chevronLeft" size={15} />{t("handling_rules.title")}</button>}
            {integrationsView?.serviceId ? <ServiceCardPage key={integrationsView.serviceId} connectionId={integrationsView.serviceId} onOpenScenario={openScenario} onBack={() => setRoute("serviceIntegrations")} /> : <>
            {current.key !== "templates" && current.key !== "scenarios" && <header className="settings-head">
              {mobile && (
                <button className="settings-head-back" type="button" aria-label={t("settings.back_section_list")} onClick={() => openSection(null)}>
                  <Icon name="chevronLeft" size={18} />
                </button>
              )}
              <div>
                <h2>{journal ? t("handling_rules.journal_title") : current.heading}</h2>
                {!journal && <p>{current.lead}</p>}
              </div>
              {headAction}
            </header>}
            {journal ? <RuleJournalCard key={user.organizationPublicId} openConversation={openConversation} /> : <SettingsSectionBody
              section={current.key}
              user={user}
              onUserUpdated={onUserUpdated}
              reload={reload}
              groups={groups}
              integrations={integrations}
              providers={providers}
              onEditIntegration={(item) => item.provider === "WEB" || item.kind === "EXTERNAL_SERVER" ? openWebIntegration(item.id) : setForm({ kind: item.kind, initial: item })}
              integrationsTab={integrationsTab}
              openIntegrationsTab={openIntegrationsTab}
              openServiceConnection={openServiceConnection}
              onTemplatesChanged={templates.reload}
              openJournal={() => setRoute("ruleJournal")}
            />}
            </>}
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

import { isManager } from "../../auth/access";
import type { EmployeeGroup, RouteKey, SessionUser } from "../../types";
import { EmptyState } from "../../shared/ui";
import { Icon } from "../../shared/icons";
import { useMediaQuery } from "../../shared/useMediaQuery";
import { DEFAULT_SETTINGS_SECTION, visibleSettingsSections, type SettingsSectionKey } from "./sections";
import { SettingsSectionBody } from "./SettingsSectionBody";
import { SettingsNavigation } from "./SettingsNavigation";
import { RuleJournalCard } from "../handling-rules/RuleJournalCard";
import { useReplyTemplates } from "./useReplyTemplates";
import { t } from "../../i18n";

export function SettingsPage({ user, onUserUpdated, reload, groups = [], section, openSection, setRoute, journal = false, openConversation }: {
  user: SessionUser;
  onUserUpdated: (user: SessionUser) => void;
  reload: () => void;
  groups?: EmployeeGroup[];
  section: SettingsSectionKey | null;
  openSection: (section: SettingsSectionKey | null) => void;
  setRoute: (route: RouteKey) => void;
  journal?: boolean;
  openConversation: (id: number) => void;
}) {
  const manager = isManager(user);
  const templates = useReplyTemplates(manager);
  // Кадр M: на узком экране субменю и раздел — два отдельных экрана.
  const mobile = useMediaQuery("(max-width: 900px)");

  if (!manager) return <EmptyState title={t("settings.settings_available_owner_administrators")} />;

  const counts: Partial<Record<SettingsSectionKey, number>> = {
    groups: groups.length,
    templates: templates.items.length,
  };
  const active = journal ? "rules" : section ?? (mobile ? null : DEFAULT_SETTINGS_SECTION);
  // Разделы про саму установку видит только её администратор.
  const sections = visibleSettingsSections(user);
  const current = sections.find((item) => item.key === active) ?? null;

  return (
    <div className="settings-layout">
      <SettingsNavigation user={user} active={active} hidden={mobile && !!current} counts={counts} openSection={openSection} setRoute={setRoute} />
      {current && (
        <section className={`settings-content ${mobile ? "is-single" : ""}`}>
          <div className="settings-content-inner">
            {journal && <button className="link is-muted has-icon" type="button" onClick={() => openSection("rules")}><Icon name="chevronLeft" size={15} />{t("handling_rules.title")}</button>}
            {current.key !== "templates" && <header className="settings-head">
              {mobile && (
                <button className="settings-head-back" type="button" aria-label={t("settings.back_section_list")} onClick={() => openSection(null)}>
                  <Icon name="chevronLeft" size={18} />
                </button>
              )}
              <div>
                <h2>{journal ? t("handling_rules.journal_title") : current.heading}</h2>
                {!journal && <p>{current.lead}</p>}
              </div>
            </header>}
            {journal ? <RuleJournalCard key={user.organizationPublicId} openConversation={openConversation} /> : <SettingsSectionBody
              section={current.key}
              user={user}
              onUserUpdated={onUserUpdated}
              reload={reload}
              groups={groups}
              onTemplatesChanged={templates.reload}
              openJournal={() => setRoute("ruleJournal")}
            />}
          </div>
        </section>
      )}
    </div>
  );
}

import { t } from '../../../../apps/internal-ui/src/i18n';
import { Icon } from '../../../../apps/internal-ui/src/shared/icons';
import { visibleSettingsGroups } from '../../../../apps/internal-ui/src/features/settings/navigation';
import { user } from './design-data';
import { tx } from './copy';

// Current SettingsNavigation presentation with the owner's one approved addition.
export function ExternalSettingsNavigation({ hidden }: { hidden: boolean }) {
  const groups = visibleSettingsGroups(user).map(group => ({
    ...group,
    sections: group.key === 'service'
      ? [...group.sections, { key: 'externalExecution', label: tx('sectionTitle'), icon: 'server' as const }]
      : group.sections,
  }));
  return <nav className={`settings-subnav ${hidden ? 'is-hidden' : ''}`} aria-label={t('common.settings')}>
    <div className="settings-subnav-head"><h2>{t('common.settings')}</h2></div>
    <div className="settings-subnav-list">
      {groups.map(group => <div className="settings-subnav-group" key={group.key} role="group" aria-labelledby={`settings-group-${group.key}`}>
        <div className="settings-subnav-caption settings-subnav-group-caption" id={`settings-group-${group.key}`}>{group.label}</div>
        {group.sections.map(item => <button type="button" key={item.key} data-settings-item={item.key}
          className={`settings-subnav-item ${item.key === 'externalExecution' ? 'is-active' : ''}`}
          aria-current={item.key === 'externalExecution' ? 'page' : undefined}>
          <Icon name={item.icon} size={16} strokeWidth={1.9} /><span>{item.label}</span>
          <span className="settings-subnav-chevron"><Icon name="chevronRight" size={16} strokeWidth={2} /></span>
        </button>)}
      </div>)}
      <div className="settings-subnav-divider" />
      <div className="settings-subnav-caption">{t('settings.separate_screens')}</div>
      <button className="settings-subnav-link" type="button"><Icon name="list" size={16} strokeWidth={1.9} />
        <span>{t('settings.action_audit')}</span><Icon name="external" size={13} strokeWidth={2} /></button>
    </div>
  </nav>;
}

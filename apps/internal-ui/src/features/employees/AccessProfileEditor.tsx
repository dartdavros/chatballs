import { useEffect, useMemo, useState } from "react";

import { Icon } from "../../shared/icons";
import type { AccessProfile, CapabilityDefinition } from "../../types";
import { editableProfile, formatScopes, groupCapabilities } from "./access-model";
import { saveAccessProfile } from "./access-api";

export function AccessProfileEditor({ capabilities, profile, reload }: {
  capabilities: CapabilityDefinition[];
  profile: AccessProfile | null;
  reload: () => void;
}) {
  const [selected, setSelected] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const groups = useMemo(() => groupCapabilities(capabilities), [capabilities]);
  const canEdit = editableProfile(profile);

  useEffect(() => {
    setSelected(profile?.capabilities ?? []);
    setError("");
  }, [profile]);

  async function save() {
    if (!profile || !canEdit || saving) return;
    setSaving(true); setError("");
    try {
      await saveAccessProfile({
        id: profile.id,
        name: profile.name,
        description: profile.description,
        capabilities: selected,
        isActive: profile.isActive,
      });
      reload();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Ошибка сохранения");
    } finally {
      setSaving(false);
    }
  }

  async function toggleActive() {
    if (!profile || profile.isSystem) return;
    setSaving(true); setError("");
    try {
      await saveAccessProfile({ ...profile, isActive: !profile.isActive });
      reload();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Ошибка сохранения");
    } finally {
      setSaving(false);
    }
  }

  function toggleCapability(item: CapabilityDefinition) {
    if (!canEdit || item.protected || !item.assignable) return;
    setSelected((items) => items.includes(item.code) ? items.filter((code) => code !== item.code) : [...items, item.code]);
  }

  if (!profile) return null;
  return (
    <section className="access-profile-editor">
      <header>
        <div className="access-profile-editor-title">
          <div><h2>{profile.name}</h2>{profile.isSystem && <b>SYSTEM</b>}</div>
          <p>{profile.description}</p>
        </div>
        <div className="access-profile-editor-actions">
          <button className="secondary-button" type="button" disabled={profile.isSystem || saving} onClick={toggleActive}>{profile.isActive ? "Отключить" : "Включить"}</button>
          <button className="primary-button" type="button" disabled={!canEdit || saving} onClick={save}>{saving ? "Сохранение" : "Сохранить"}</button>
        </div>
      </header>
      <div className="access-profile-summary"><span>Разрешённые scopes: <b>{formatScopes(profile.allowedScopes)}</b></span><span>Назначено сотрудникам: <b>{profile.assignedCount}</b></span></div>
      <div className="access-capabilities-header"><h3>Capability</h3><span>Каталог задан кодом приложения · произвольные коды запрещены</span></div>
      <div className="access-capability-groups">
        {groups.map((group) => <section key={group.domain}><h4>{group.domain}</h4><div>{group.capabilities.map((item) => { const checked = selected.includes(item.code); const locked = item.protected || !item.assignable; return <button className={`${checked ? "checked" : ""} ${locked ? "protected" : ""}`} type="button" disabled={!canEdit || locked} onClick={() => toggleCapability(item)} key={item.code}><i>{checked && <Icon name="check" size={11} />}</i><span><code>{item.code}</code>{locked && <b>OWNER</b>}<small>{item.name}</small></span></button>; })}</div></section>)}
      </div>
      <div className="access-protected-note"><Icon name="lock" size={15} /><p>Защищённые capability <code>employees.manage_privileged</code> и <code>ownership.transfer</code> нельзя включить в профиль — они доступны только владельцу.</p></div>
      {error && <div className="access-profile-error">{error}</div>}
    </section>
  );
}

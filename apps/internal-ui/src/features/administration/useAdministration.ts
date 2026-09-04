import { useCallback, useEffect, useState } from "react";

import { api, ApiError } from "../../api/client";
import { hasCapability } from "../../auth/access";
import type { SessionUser } from "../../types";
import {
  loadAudit,
  loadOrganizationSettings,
  removeOrganizationLogo,
  saveOrganizationSettings,
  uploadOrganizationLogo,
} from "./api";
import type {
  AdministrationSection,
  AuditEvent,
  OrganizationSettings,
} from "./model";

export function useAdministration({
  section,
  user,
  onUserUpdated,
}: {
  section: AdministrationSection;
  user: SessionUser;
  onUserUpdated: (user: SessionUser) => void;
}) {
  const [organization, setOrganization] = useState<OrganizationSettings | null>(null);
  const [timezones, setTimezones] = useState<string[]>([]);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const refreshIdentity = useCallback(async () => {
    const payload = await api<{ authenticated: boolean; user?: SessionUser }>(
      "/api/v1/auth/session/",
    );
    if (payload.authenticated && payload.user) onUserUpdated(payload.user);
  }, [onUserUpdated]);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      if (section === "organization") {
        const settings = await loadOrganizationSettings();
        setOrganization(settings.organization);
        setTimezones(settings.timezones);
      } else if (section === "audit" && hasCapability(user, "audit.view")) {
        setAudit(await loadAudit());
      }
    } catch (loadError) {
      setError(loadError instanceof ApiError ? loadError.message : "Не удалось загрузить данные");
    } finally {
      setLoading(false);
    }
  }, [section, user]);

  useEffect(() => {
    void load();
  }, [load]);

  const runChange = useCallback(async (
    change: () => Promise<OrganizationSettings>,
    successMessage: string,
  ) => {
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const next = await change();
      setOrganization(next);
      setMessage(successMessage);
      await refreshIdentity();
    } catch (changeError) {
      setError(changeError instanceof ApiError ? changeError.message : "Не удалось сохранить изменения");
    } finally {
      setSaving(false);
    }
  }, [refreshIdentity]);

  return {
    audit,
    error,
    loading,
    message,
    organization,
    saving,
    timezones,
    setOrganization,
    reload: load,
    save: () => organization && runChange(
      () => saveOrganizationSettings(organization),
      "Данные организации сохранены",
    ),
    uploadLogo: (file: File) => runChange(
      () => uploadOrganizationLogo(file),
      "Логотип обновлён",
    ),
    removeLogo: () => runChange(
      removeOrganizationLogo,
      "Логотип удалён",
    ),
  };
}

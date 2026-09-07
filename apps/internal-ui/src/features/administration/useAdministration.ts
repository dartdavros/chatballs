import { useCallback, useEffect, useState } from "react";

import { api, ApiError } from "../../api/client";
import type { SessionUser } from "../../types";
import {
  loadOrganizationSettings,
  removeOrganizationLogo,
  saveOrganizationSettings,
  uploadOrganizationLogo,
} from "./api";
import type { AdministrationSection, OrganizationSettings } from "./model";

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
      const settings = await loadOrganizationSettings();
      setOrganization(settings.organization);
      setTimezones(settings.timezones);
    } catch (loadError) {
      setError(loadError instanceof ApiError ? loadError.message : "Не удалось загрузить данные");
    } finally {
      setLoading(false);
    }
  }, [section]);

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

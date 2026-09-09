import { useCallback, useEffect, useState } from "react";

import { api, ApiError } from "../../api/client";
import type { SessionUser } from "../../types";
import {
  loadOrganizationSettings,
  removeOrganizationLogo,
  saveOrganizationSettings,
  uploadOrganizationLogo,
} from "./api";
import type { OrganizationLanguageOption } from "./api";
import type { AdministrationSection, OrganizationSettings } from "./model";
import { t } from "../../i18n";

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
  const [languages, setLanguages] = useState<OrganizationLanguageOption[]>([]);
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
      setLanguages(settings.languages);
    } catch (loadError) {
      setError(loadError instanceof ApiError ? loadError.message : t("admin.could_not_load_data"));
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
      setError(changeError instanceof ApiError ? changeError.message : t("admin.could_not_save_changes"));
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
    languages,
    setOrganization,
    reload: load,
    save: () => organization && runChange(
      () => saveOrganizationSettings(organization),
      t("admin.organization_details_saved"),
    ),
    uploadLogo: (file: File) => runChange(
      () => uploadOrganizationLogo(file),
      t("admin.logo_updated"),
    ),
    removeLogo: () => runChange(
      removeOrganizationLogo,
      t("admin.logo_removed"),
    ),
  };
}

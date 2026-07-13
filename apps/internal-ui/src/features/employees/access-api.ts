import { useCallback, useEffect, useState } from "react";

import { api } from "../../api/client";
import type { AccessProfile, CapabilityDefinition } from "../../types";

export async function fetchAccessCatalog() {
  const [profiles, capabilities] = await Promise.all([
    api<{ items: AccessProfile[] }>("/api/v1/access-profiles/"),
    api<{ items: CapabilityDefinition[] }>("/api/v1/access-profiles/capabilities/"),
  ]);
  return { profiles: profiles.items, capabilities: capabilities.items };
}

export function useAccessCatalog(enabled = true) {
  const [profiles, setProfiles] = useState<AccessProfile[]>([]);
  const [capabilities, setCapabilities] = useState<CapabilityDefinition[]>([]);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    if (!enabled) return;
    setLoading(true);
    setError("");
    try {
      const catalog = await fetchAccessCatalog();
      setProfiles(catalog.profiles);
      setCapabilities(catalog.capabilities);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Ошибка загрузки");
    } finally {
      setLoading(false);
    }
  }, [enabled]);

  useEffect(() => { void reload(); }, [reload]);
  return { profiles, capabilities, loading, error, reload };
}

export function saveAccessProfile(profile: Partial<AccessProfile> & { name: string; capabilities: string[] }) {
  if (profile.id) {
    return api<{ profile: AccessProfile }>(`/api/v1/access-profiles/${profile.id}/`, {
      method: "PATCH",
      body: JSON.stringify(profile),
    });
  }
  return api<{ profile: AccessProfile }>("/api/v1/access-profiles/", {
    method: "POST",
    body: JSON.stringify(profile),
  });
}

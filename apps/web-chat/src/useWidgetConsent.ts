import { useEffect, useState } from "react";
import { sendSiteFields, startSession, type SiteFields, type WebConfig, type WidgetEntry } from "./api";
import { checkServerConsent, confirmServerConsent } from "./consentApi";
import { useSiteFields } from "./useSiteFields";

export function consentMatches(token: string | null, saved: string | null, current: string | undefined): boolean {
  return Boolean(token && current && saved === current);
}

export function useWidgetConsent(config: WebConfig | null, entry: WidgetEntry, hostOrigin: string, tokenKey: string) {
  const versionKey = `${tokenKey}:consent-version`;
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(tokenKey));
  const [version, setVersion] = useState<string | null>(() => localStorage.getItem(versionKey));
  const [starting, setStarting] = useState(false);
  const [proof, setProof] = useState<{ token: string; policy: string } | null>(null);
  const policy = JSON.stringify([config?.consent?.version, config?.preChat, config?.fields]);
  const accepted = consentMatches(token, version, config?.consent?.version)
    && proof?.token === token && proof?.policy === policy;
  const siteFields = useSiteFields(accepted ? token : null, hostOrigin);

  useEffect(() => {
    if (!token || !config?.available) return;
    const controller = new AbortController();
    void checkServerConsent(token, hostOrigin, controller.signal).then((confirmed) => {
      if (!controller.signal.aborted) setProof(confirmed ? { token, policy } : null);
    }).catch(() => { if (!controller.signal.aborted) setProof(null); });
    return () => controller.abort();
  }, [token, config?.available, hostOrigin, policy]);

  function forgetConsent() {
    localStorage.removeItem(tokenKey);
    localStorage.removeItem(versionKey);
    setToken(null);
    setVersion(null);
    setProof(null);
  }

  async function accept(preChatFields?: SiteFields) {
    if (starting || !config?.available) return;
    setStarting(true);
    try {
      const nextToken = await siteFields.start(async (fields) => {
        if (token) {
          const confirmed = await confirmServerConsent(token, hostOrigin, config.consent?.version, preChatFields);
          if (confirmed !== null) {
            return confirmed && await sendSiteFields(token, fields) ? token : null;
          }
        }
        return startSession(entry, hostOrigin, fields, preChatFields, config.consent?.version);
      });
      if (!nextToken) return;
      const nextVersion = config.consent?.version ?? "";
      localStorage.setItem(tokenKey, nextToken);
      localStorage.setItem(versionKey, nextVersion);
      setToken(nextToken);
      setVersion(nextVersion);
      setProof({ token: nextToken, policy });
    } finally { setStarting(false); }
  }

  return { token, accepted, starting, accept, forgetConsent, siteValues: siteFields.values };
}

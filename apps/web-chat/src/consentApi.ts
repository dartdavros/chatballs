import type { SiteFields } from "./api";

const ENDPOINT = "/api/v1/webchat/consent/";

export async function checkServerConsent(token: string, hostOrigin: string, signal: AbortSignal): Promise<boolean> {
  const response = await fetch(`${ENDPOINT}?hostOrigin=${encodeURIComponent(hostOrigin)}`, {
    headers: { Authorization: `Bearer ${token}` }, signal, cache: "no-store",
  });
  return response.ok && (await response.json()).accepted === true;
}

export async function confirmServerConsent(token: string, hostOrigin: string, version: string | undefined, fields?: SiteFields): Promise<boolean | null> {
  const response = await fetch(ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ hostOrigin, consentVersion: version, preChatFields: fields }),
  });
  if (response.status === 401) return null;
  return response.ok;
}

export class SynthesisError extends Error {
  constructor(readonly code: string) { super(code); }
}

export async function synthesizeAnswer(token: string, messageId: number, revision: string, hostOrigin: string, signal: AbortSignal): Promise<Blob> {
  const timeout = AbortSignal.timeout(185_000);
  const response = await fetch(`/api/v1/webchat/messages/${messageId}/synthesis/`, {
    method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ revision, hostOrigin }), signal: AbortSignal.any([signal, timeout]), cache: "no-store",
  });
  if (!response.ok) {
    const result = await response.json().catch(() => ({}));
    throw new SynthesisError(result.code || "tts_provider_error");
  }
  if (!response.headers.get("Content-Type")?.startsWith("audio/wav")) throw new SynthesisError("tts_provider_error");
  const blob = await response.blob();
  if (!blob.size || blob.size > 64 * 1024 * 1024 + 44) throw new SynthesisError("tts_provider_error");
  return blob;
}

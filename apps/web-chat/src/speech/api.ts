export class RecognitionError extends Error {
  constructor(readonly code: string) { super(code); }
}

export async function recognize(token: string, audio: Blob, hostOrigin: string, signal: AbortSignal): Promise<string> {
  const body = new FormData();
  body.append("audio", audio, "dictation");
  body.append("hostOrigin", hostOrigin);
  const response = await fetch("/api/v1/webchat/dictation/", {
    method: "POST", headers: { Authorization: `Bearer ${token}` }, body, signal,
  });
  const result = await response.json();
  if (!response.ok) throw new RecognitionError(result.code || "provider_error");
  if (typeof result.text !== "string" || !result.text.trim()) throw new RecognitionError("empty");
  return result.text;
}

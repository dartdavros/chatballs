import { api } from "../../api/client";

export async function downloadDiagnostic(conversationId: number): Promise<void> {
  const data = await api<unknown>(`/api/v1/conversations/${conversationId}/diagnostic/`);
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], {
    type: "application/json;charset=utf-8",
  }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `chatballs-dialog-${conversationId}-diagnostic.json`;
  document.body.appendChild(link);
  try { link.click(); }
  finally {
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
}

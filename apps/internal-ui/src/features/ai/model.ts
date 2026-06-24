export type AiAgent = {
  id: number;
  product: { code: string; name: string };
  name: string;
  isActive: boolean;
  model: string;
  modelParams: Record<string, unknown>;
  allowedTools: unknown[];
  limits: Record<string, unknown>;
};

export type AiRelease = {
  id: number;
  product: { code: string; name: string };
  version: number;
  status: "DRAFT" | "PUBLISHED" | "ARCHIVED";
};

const PRODUCT_ACCENTS: Record<string, { bg: string; color: string }> = {
  firepage: { bg: "#e6f4ff", color: "#0958d9" },
  foxray: { bg: "#f9f0ff", color: "#722ed1" },
};

export function productAccent(code: string): { bg: string; color: string } {
  return PRODUCT_ACCENTS[code] ?? { bg: "#f5f5f5", color: "#595959" };
}

export function agentStatus(agent: AiAgent): { label: string; color: string; dot: string } {
  return agent.isActive
    ? { label: "Активен", color: "#389e0d", dot: "#52c41a" }
    : { label: "Остановлен", color: "#d48806", dot: "#faad14" };
}

export function publishedRelease(releases: AiRelease[], productCode: string): AiRelease | undefined {
  return releases.find((release) => release.product.code === productCode && release.status === "PUBLISHED");
}

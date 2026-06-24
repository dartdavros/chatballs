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

export function publishedRelease(releases: AiRelease[], productCode: string): AiRelease | undefined {
  return releases.find((release) => release.product.code === productCode && release.status === "PUBLISHED");
}

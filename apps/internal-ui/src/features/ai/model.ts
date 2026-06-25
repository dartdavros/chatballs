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

export function releaseName(release: AiRelease): string {
  const letters = release.product.name.match(/[A-ZА-ЯЁ]/g)?.join("");
  const prefix = letters && letters.length >= 2 ? letters.slice(0, 2) : release.product.code.slice(0, 2);
  return `REL-${prefix.toUpperCase()}-v${release.version}`;
}

export type ChannelRef = { id: number; code: string; name: string; product: { code: string; name: string } | null };

export type AiAgent = {
  id: number;
  channel: ChannelRef;
  name: string;
  isActive: boolean;
  model: string;
  modelParams: Record<string, unknown>;
  allowedTools: unknown[];
  limits: Record<string, unknown>;
};

export type AiRelease = {
  id: number;
  channel: ChannelRef;
  version: number;
  status: "DRAFT" | "PUBLISHED" | "ARCHIVED";
};

export function publishedRelease(releases: AiRelease[], channelCode: string): AiRelease | undefined {
  return releases.find((release) => release.channel.code === channelCode && release.status === "PUBLISHED");
}

export function releaseName(release: AiRelease): string {
  const letters = release.channel.name.match(/[A-ZА-ЯЁ]/g)?.join("");
  const prefix = letters && letters.length >= 2 ? letters.slice(0, 2) : release.channel.code.slice(0, 2);
  return `REL-${prefix.toUpperCase()}-v${release.version}`;
}

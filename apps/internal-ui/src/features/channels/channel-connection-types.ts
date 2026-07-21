export type ConnectionCandidate = {
  id: number;
  kind: string;
  provider: string;
  name: string;
  externalId?: string | null;
  channelId: number | null;
};

export type ConnectionTransfer = { integration: ConnectionCandidate; fromChannel: string };

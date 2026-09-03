export type ClientProductCode = "FP" | "FX";
export type ClientChannelCode = "EMAIL" | "MAX" | "TG" | "WEB";
export type ClientSortKey = "last" | "open";
export type ClientDropdown = "products" | "channels";

export type SalesClient = {
  id: number;
  name: string;
  initials: string;
  avatarBg: string;
  cid: string;
  phone: string;
  email: string;
  username: string;
  anon?: boolean;
  channels: ClientChannelCode[];
  products: ClientProductCode[];
  last: number;
  lastLabel: string;
  mode: "wait" | "ai" | "operator" | "closed";
  openDialogs: number;
};

export type SalesClientRowVm = Omit<SalesClient, "channels" | "products"> & {
  lastDot: string;
  openColor: string;
  channels: Array<{ label: string; full: string; color: string; bg: string }>;
  products: Array<{ name: string; color: string; bg: string }>;
};

export const channelMap = {
  EMAIL: { label: "Email", full: "Email", color: "#d48806", bg: "#fff7e6" },
  MAX: { label: "MAX", full: "MAX", color: "#6b5be0", bg: "#f2f0ff" },
  TG: { label: "TG", full: "Telegram", color: "#2f8fd0", bg: "#eaf6fd" },
  WEB: { label: "Web", full: "Web Chat", color: "#0f9b8e", bg: "#e8f7f4" },
} satisfies Record<ClientChannelCode, { label: string; full: string; color: string; bg: string }>;

export const productMap = {
  FP: { name: "FirePage", color: "#0958d9", bg: "#e6f4ff" },
  FX: { name: "Foxray", color: "#722ed1", bg: "#f9f0ff" },
} satisfies Record<ClientProductCode, { name: string; color: string; bg: string }>;

export const channelOptions: Array<{ code: ClientChannelCode; name: string; color: string }> = [
  { code: "EMAIL", name: "Email", color: channelMap.EMAIL.color },
  { code: "MAX", name: "MAX", color: channelMap.MAX.color },
  { code: "TG", name: "Telegram", color: channelMap.TG.color },
  { code: "WEB", name: "Web Chat", color: channelMap.WEB.color },
];

export const productOptions: Array<{ code: ClientProductCode; name: string }> = [
  { code: "FP", name: "FirePage" },
  { code: "FX", name: "Foxray" },
];

const statusDot = {
  wait: "#faad14",
  ai: "#722ed1",
  operator: "#1677ff",
  closed: "#bfbfbf",
} satisfies Record<SalesClient["mode"], string>;

// Реальный контакт с бэкенда (conversations/clients.py).
export type ApiClient = {
  id: number;
  cid: string;
  name: string;
  phone: string;
  email: string;
  username: string;
  channels: ClientChannelCode[];
  products: ClientProductCode[];
  openDialogs: number;
  totalDialogs: number;
  lastActivityAt: string;
  mode: SalesClient["mode"];
};

const AVATAR_COLORS = ["#eb6f4b", "#3b82c4", "#9254de", "#13a8a8", "#d4860b", "#52a838", "#c4456b", "#4c6ef0", "#7048b6"];

export function initialsOf(name: string): string {
  const words = name.replace(/·.*/, "").trim().split(/\s+/).filter(Boolean);
  const letters = words.slice(0, 2).map((word) => word[0]).join("");
  return (letters || name.slice(0, 2)).toUpperCase();
}

export function avatarColor(seed: string): string {
  let hash = 0;
  for (let index = 0; index < seed.length; index += 1) hash = (hash * 31 + seed.charCodeAt(index)) >>> 0;
  return AVATAR_COLORS[hash % AVATAR_COLORS.length];
}

export function relativeTime(iso: string): { minutes: number; label: string } {
  const minutes = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (minutes < 60) return { minutes, label: `${minutes} мин назад` };
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return { minutes, label: `${hours} ч назад` };
  return { minutes, label: `${Math.floor(hours / 24)} д назад` };
}

export function toSalesClient(api: ApiClient): SalesClient {
  const isGuest = /гость/i.test(api.name);
  const { minutes, label } = relativeTime(api.lastActivityAt);
  return {
    id: api.id,
    name: api.name,
    initials: initialsOf(api.name),
    avatarBg: isGuest ? "#8c8c8c" : avatarColor(api.cid),
    cid: api.cid,
    phone: api.phone,
    email: api.email,
    username: api.username,
    anon: isGuest,
    channels: api.channels,
    products: api.products,
    last: minutes,
    lastLabel: label,
    mode: api.mode,
    openDialogs: api.openDialogs,
  };
}

export function toSalesClientRow(client: SalesClient): SalesClientRowVm {
  return {
    ...client,
    channels: client.channels.map((channel) => channelMap[channel]),
    products: client.products.map((product) => productMap[product]),
    lastDot: statusDot[client.mode],
    openColor: client.openDialogs > 0 ? "#d48806" : "#bfbfbf",
  };
}

export type ClientProductCode = "FP" | "FX";
export type ClientChannelCode = "MAX" | "TG" | "WEB";
export type ClientSortKey = "last" | "open" | "orders" | "total";
export type ClientDropdown = "products" | "channels";

export type SalesClient = {
  name: string;
  initials: string;
  avatarBg: string;
  cid: string;
  email: string;
  phone: string;
  anon?: boolean;
  channels: ClientChannelCode[];
  products: ClientProductCode[];
  last: number;
  lastLabel: string;
  mode: "wait" | "ai" | "operator" | "closed";
  openDialogs: number;
  orders: number;
  total: number;
};

export type SalesClientRowVm = Omit<SalesClient, "channels" | "products"> & {
  lastDot: string;
  openColor: string;
  totalColor: string;
  totalLabel: string;
  channels: Array<{ label: string; full: string; color: string; bg: string }>;
  products: Array<{ name: string; color: string; bg: string }>;
};

export const channelMap = {
  MAX: { label: "MAX", full: "MAX", color: "#6b5be0", bg: "#f2f0ff" },
  TG: { label: "TG", full: "Telegram", color: "#2f8fd0", bg: "#eaf6fd" },
  WEB: { label: "Web", full: "Web Chat", color: "#0f9b8e", bg: "#e8f7f4" },
} satisfies Record<ClientChannelCode, { label: string; full: string; color: string; bg: string }>;

export const productMap = {
  FP: { name: "FirePage", color: "#0958d9", bg: "#e6f4ff" },
  FX: { name: "Foxray", color: "#722ed1", bg: "#f9f0ff" },
} satisfies Record<ClientProductCode, { name: string; color: string; bg: string }>;

export const channelOptions: Array<{ code: ClientChannelCode; name: string; color: string }> = [
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

export const salesClients: SalesClient[] = [
  { name: "Мария Соколова", initials: "МС", avatarBg: "#eb6f4b", cid: "CUS-4821", email: "m.sokolova@workmail.ru", phone: "+7 ··· ·· 14", channels: ["MAX"], products: ["FP"], last: 5, lastLabel: "5 мин назад", mode: "wait", openDialogs: 1, orders: 0, total: 0 },
  { name: "Дмитрий Орлов", initials: "ДО", avatarBg: "#3b82c4", cid: "CUS-4789", email: "d.orlov@gmail.com", phone: "+7 ··· ·· 03", channels: ["TG"], products: ["FX"], last: 8, lastLabel: "8 мин назад", mode: "ai", openDialogs: 1, orders: 2, total: 4980 },
  { name: "Елена Кузнецова", initials: "ЕК", avatarBg: "#9254de", cid: "CUS-4702", email: "e.kuznetsova@corp.ru", phone: "+7 ··· ·· 88", channels: ["MAX", "WEB"], products: ["FX", "FP"], last: 18, lastLabel: "18 мин назад", mode: "operator", openDialogs: 1, orders: 3, total: 12470 },
  { name: "Сергей Волков", initials: "СВ", avatarBg: "#13a8a8", cid: "CUS-4655", email: "s.volkov@mail.ru", phone: "+7 ··· ·· 21", channels: ["TG"], products: ["FP"], last: 26, lastLabel: "26 мин назад", mode: "ai", openDialogs: 1, orders: 1, total: 2490 },
  { name: "Ольга Зайцева", initials: "ОЗ", avatarBg: "#d4860b", cid: "CUS-4590", email: "o.zaytseva@yandex.ru", phone: "+7 ··· ·· 47", channels: ["WEB"], products: ["FX"], last: 35, lastLabel: "35 мин назад", mode: "operator", openDialogs: 1, orders: 0, total: 0 },
  { name: "Павел Новиков", initials: "ПН", avatarBg: "#52a838", cid: "CUS-4410", email: "p.novikov@firm.io", phone: "+7 ··· ·· 60", channels: ["MAX"], products: ["FP"], last: 60, lastLabel: "1 ч назад", mode: "closed", openDialogs: 0, orders: 4, total: 19600 },
  { name: "Анна Морозова", initials: "АМ", avatarBg: "#c4456b", cid: "CUS-4322", email: "a.morozova@studio.com", phone: "+7 ··· ·· 12", channels: ["TG", "MAX"], products: ["FP", "FX"], last: 180, lastLabel: "3 ч назад", mode: "closed", openDialogs: 0, orders: 6, total: 31200 },
  { name: "Гость 8842", initials: "Г8", avatarBg: "#8c8c8c", cid: "CUS-4901", email: "без контакта", phone: "идентификация по каналу", anon: true, channels: ["WEB"], products: ["FP"], last: 12, lastLabel: "12 мин назад", mode: "wait", openDialogs: 1, orders: 0, total: 0 },
  { name: "Игорь Соколов", initials: "ИС", avatarBg: "#4c6ef0", cid: "CUS-4188", email: "i.sokolov@dev.team", phone: "+7 ··· ·· 35", channels: ["MAX"], products: ["FX"], last: 300, lastLabel: "5 ч назад", mode: "closed", openDialogs: 0, orders: 2, total: 6970 },
  { name: "Татьяна Лебедева", initials: "ТЛ", avatarBg: "#7048b6", cid: "CUS-3980", email: "t.lebedeva@agency.ru", phone: "+7 ··· ·· 99", channels: ["TG", "MAX"], products: ["FP"], last: 1440, lastLabel: "1 д назад", mode: "closed", openDialogs: 0, orders: 8, total: 42800 },
];

export function toSalesClientRow(client: SalesClient): SalesClientRowVm {
  return {
    ...client,
    channels: client.channels.map((channel) => channelMap[channel]),
    products: client.products.map((product) => productMap[product]),
    lastDot: statusDot[client.mode],
    openColor: client.openDialogs > 0 ? "#d48806" : "#bfbfbf",
    totalColor: client.total > 0 ? "#262626" : "#bfbfbf",
    totalLabel: client.total === 0 ? "—" : `₽${client.total.toLocaleString("ru-RU").replace(/\u00a0/g, " ")}`,
  };
}

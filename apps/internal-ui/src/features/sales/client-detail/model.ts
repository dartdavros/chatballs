import { agentColorOf, groupColorOf } from "../../conversations/model";
import { shortDate, shortDateTime } from "../../../shared/utils";
import { avatarColor, channelMap, contactTime, initialsOf, type ClientChannelCode } from "../clients/model";

// Карточка контакта (дизайн-базлайн v2, кадры K3–K5). Вкладка «Согласия»
// убрана — журнал согласий отдельной сущностью не ведётся; блока «Связанные
// продукты» нет (ADR-HUB-0041).

export type ClientDetailTab = "overview" | "dialogs" | "ids" | "audit";

const PROVIDER_TO_CHANNEL: Record<string, ClientChannelCode> = { EMAIL: "EMAIL", MAX: "MAX", TELEGRAM: "TG", WEB: "WEB" };
const PROVIDER_LABEL: Record<string, string> = { EMAIL: "Email", MAX: "MAX", TELEGRAM: "Telegram", WEB: "Web-виджет" };

// Подпись и цвет режима диалога — те же, что в чате и в списке контактов.
const MODE_META: Record<ClientDialogMode, { label: string; color: string; bg: string; dot: string }> = {
  ai: { label: "AI отвечает", color: "var(--ai)", bg: "color-mix(in srgb, var(--ai) 14%, var(--surface-card))", dot: "var(--ai)" },
  wait: { label: "Ждёт", color: "var(--warning-text)", bg: "var(--warning-bg)", dot: "#faad14" },
  operator: { label: "Ведёт человек", color: "var(--primary-text)", bg: "var(--primary-bg)", dot: "var(--primary)" },
  closed: { label: "Закрыт", color: "var(--n-4)", bg: "var(--n-9)", dot: "var(--n-5)" },
};

export type ClientDialogMode = "ai" | "wait" | "operator" | "closed";

export type ApiClientDetail = {
  id: number;
  cid: string;
  name: string;
  avatarUrl?: string;
  description?: string;
  company?: string;
  city?: string;
  email: string;
  phone: string;
  channels: ClientChannelCode[];
  openDialogs: number;
  totalDialogs: number;
  firstContactAt: string;
  lastActivityAt: string;
  dialogs: Array<{
    id: number;
    title: string;
    preview: string;
    channelName: string;
    agentId: number;
    agentName: string;
    agentCode: string;
    groupName: string;
    groupColor: string;
    assignee: string;
    assigneeAvatarUrl: string | null;
    note: string;
    noteAuthor: string;
    noteUpdatedAt: string | null;
    provider: string | null;
    mode: ClientDialogMode;
    status: string;
    active: boolean;
    lastActivityAt: string;
  }>;
  identities: Array<{ provider: string; value: string; externalUserId: string; username: string; createdAt: string; phoneVerifiedAt: string | null }>;
  activity: Array<{ type: "created" | "closed"; title: string; at: string }>;
  audit: Array<{ time: string; action: string; object: string; actor: string; result: string }>;
  duplicate: { id: number; cid: string; name: string; avatarUrl: string; dialogs: number; sources: string[]; phone: string; phoneVerified: boolean } | null;
  merges: Array<{ id: number; sourceId: number; sourceName: string; sourceCid: string; reason: string; actor: string; at: string; identities: number; conversations: number }>;
};

export type ClientDetailDialogVm = {
  id: number;
  title: string;
  preview: string;
  agentName: string;
  agentColor: string;
  channelLabel: string;
  groupName: string;
  groupColor: string;
  assignee: string;
  assigneeAvatarUrl: string;
  note: string;
  noteAuthor: string;
  noteAt: string;
  mode: ClientDialogMode;
  modeLabel: string;
  modeColor: string;
  modeBg: string;
  dot: string;
  active: boolean;
  time: string;
};

export type ClientDetailVm = {
  id: number;
  cid: string;
  name: string;
  initials: string;
  avatarBg: string;
  avatarUrl: string;
  description: string;
  company: string;
  city: string;
  email: string;
  phone: string;
  rawPhone: string;
  channels: Array<{ code: ClientChannelCode; full: string; color: string; bg: string }>;
  totalDialogs: number;
  summary: Array<{ label: string; value: string; accent?: boolean; compact?: boolean }>;
  dialogs: ClientDetailDialogVm[];
  identities: Array<{ code: ClientChannelCode | null; name: string; value: string; since: string; status: string; confirmed: boolean; color: string; bg: string }>;
  activity: Array<{ title: string; time: string; color: string }>;
  audit: Array<{ time: string; action: string; object: string; actor: string; result: string }>;
  duplicate: ApiClientDetail["duplicate"] & { initials: string; sourceLabel: string } | null;
  // Действующие объединения — их можно разъединить (ADR-HUB-0006).
  merges: Array<ApiClientDetail["merges"][number] & { atLabel: string }>;
};

export const clientDetailTabsOf = (client: ClientDetailVm): Array<{ key: ClientDetailTab; label: string; count?: number }> => [
  { key: "overview", label: "Обзор" },
  { key: "dialogs", label: "Диалоги", count: client.totalDialogs },
  { key: "ids", label: "Идентификаторы", count: client.identities.length },
  { key: "audit", label: "Аудит" },
];

export function toClientDetailVm(api: ApiClientDetail): ClientDetailVm {
  const isGuest = /гость/i.test(api.name);
  const duplicate = api.duplicate;
  return {
    id: api.id,
    cid: api.cid,
    name: api.name,
    initials: initialsOf(api.name),
    avatarBg: isGuest ? "var(--n-4)" : avatarColor(api.cid),
    avatarUrl: api.avatarUrl ?? "",
    description: api.description ?? "",
    company: api.company ?? "",
    city: api.city ?? "",
    email: api.email,
    phone: api.phone,
    rawPhone: api.phone ?? "",
    channels: api.channels.map((code) => ({ code, ...channelMap[code] })),
    totalDialogs: api.totalDialogs,
    summary: [
      { label: "Диалогов", value: String(api.totalDialogs) },
      { label: "Открытых", value: String(api.openDialogs), accent: api.openDialogs > 0 },
      { label: "Первый контакт", value: shortDate(api.firstContactAt), compact: true },
      { label: "Последняя активность", value: contactTime(api.lastActivityAt), compact: true },
    ],
    dialogs: api.dialogs.map((dialog) => {
      const meta = MODE_META[dialog.mode];
      return {
        id: dialog.id,
        title: dialog.title,
        preview: dialog.preview,
        agentName: dialog.agentName,
        agentColor: agentColorOf(dialog.agentId),
        channelLabel: dialog.provider ? PROVIDER_LABEL[dialog.provider] ?? dialog.provider : "",
        groupName: dialog.groupName,
        groupColor: dialog.groupColor || groupColorOf(dialog.id),
        assignee: dialog.assignee,
        assigneeAvatarUrl: dialog.assigneeAvatarUrl ?? "",
        note: dialog.note,
        noteAuthor: dialog.noteAuthor,
        noteAt: dialog.noteUpdatedAt ? shortDate(dialog.noteUpdatedAt) : "",
        mode: dialog.mode,
        modeLabel: meta.label,
        modeColor: meta.color,
        modeBg: meta.bg,
        dot: meta.dot,
        active: dialog.active,
        time: contactTime(dialog.lastActivityAt),
      };
    }),
    identities: api.identities.map((identity) => {
      const code = PROVIDER_TO_CHANNEL[identity.provider] ?? null;
      const meta = code ? channelMap[code] : { color: "var(--n-4)", bg: "var(--n-9)" };
      const confirmed = Boolean(identity.phoneVerifiedAt);
      return {
        code,
        name: PROVIDER_LABEL[identity.provider] ?? identity.provider,
        value: [identity.externalUserId, identity.username ? `@${identity.username}` : ""].filter(Boolean).join(" · "),
        since: `с ${shortDate(identity.createdAt)}`,
        status: confirmed ? "Подтверждён телефоном" : "Не подтверждён",
        confirmed,
        color: meta.color,
        bg: meta.bg,
      };
    }),
    activity: api.activity.map((event) => ({
      title: event.title,
      time: shortDateTime(event.at),
      color: event.type === "closed" ? "var(--n-5)" : "var(--primary)",
    })),
    audit: api.audit.map((event) => ({
      time: shortDateTime(event.time),
      action: event.action,
      object: event.object,
      actor: event.actor,
      result: event.result,
    })),
    duplicate: duplicate
      ? {
        ...duplicate,
        initials: initialsOf(duplicate.name),
        sourceLabel: [
          duplicate.sources.map((provider) => PROVIDER_LABEL[provider] ?? provider).join(", "),
          `${duplicate.dialogs} диал.`,
          maskPhone(duplicate.phone),
        ].filter(Boolean).join(" · "),
      }
      : null,
    merges: (api.merges ?? []).map((merge) => ({ ...merge, atLabel: shortDateTime(merge.at) })),
  };
}

// Телефон дубликата показываем частично: «+7 916 ••• 44-10» (кадр K5).
function maskPhone(phone: string): string {
  const digits = phone.replace(/\D/g, "");
  if (digits.length < 7) return phone;
  return `${phone.slice(0, phone.length - 7).trim()} ••• ${phone.slice(-5)}`;
}

export function initials(name: string, email: string): string {
  const source = name.trim() || email.split("@")[0] || "CB";
  const parts = source.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  return source.slice(0, 2).toUpperCase();
}

export function formatDate(value: string): string {
  return new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "long", year: "numeric" }).format(new Date(value));
}

/** Склонение по числу: pluralRu(3, ["портал", "портала", "порталов"]) → «3 портала». */
export function pluralRu(count: number, forms: [string, string, string]): string {
  const n = Math.abs(count) % 100;
  const n1 = n % 10;
  const form = n > 10 && n < 20 ? forms[2] : n1 > 1 && n1 < 5 ? forms[1] : n1 === 1 ? forms[0] : forms[2];
  return `${count} ${form}`;
}

/** Подпись часового пояса со смещением: «Europe/Moscow · UTC+3» (кадр N1). */
export function timezoneLabel(zone: string, now = new Date()): string {
  try {
    const parts = new Intl.DateTimeFormat("en-US", { timeZone: zone, timeZoneName: "longOffset" }).formatToParts(now);
    const raw = parts.find((part) => part.type === "timeZoneName")?.value ?? "";
    const match = raw.match(/GMT([+-])(\d{2}):(\d{2})/);
    if (!match) return `${zone} · UTC+0`;
    const [, sign, hours, minutes] = match;
    const suffix = minutes === "00" ? String(Number(hours)) : `${Number(hours)}:${minutes}`;
    return `${zone} · UTC${sign}${suffix}`;
  } catch {
    return zone;
  }
}

// Даты дизайн-базлайна v2 пишутся коротким месяцем без точки: «2 сен, 14:12»
// (кадры N1/N3/N6/N7). Intl даёт «2 сент.», поэтому месяц берём из списка.
const SHORT_MONTHS = ["янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"];

export function shortDate(value: string | Date): string {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return `${date.getDate()} ${SHORT_MONTHS[date.getMonth()]}`;
}

/** «12 авг 2026» — короткий месяц без точки плюс год (кадры E1/E3, G3). */
export function shortDateYear(value: string | Date): string {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return `${shortDate(date)} ${date.getFullYear()}`;
}

export function shortDateTime(value: string | Date): string {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const time = date.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
  return `${shortDate(date)}, ${time}`;
}

/** «янв 2026» — дата вступления в организацию в шапке «Профиля» (кадр P1).
 *  Стоит после предлога «с», поэтому месяц в родительном падеже — «с мая». */
export function monthYear(value: string | Date): string {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return `${SHORT_MONTHS[date.getMonth()]} ${date.getFullYear()}`;
}

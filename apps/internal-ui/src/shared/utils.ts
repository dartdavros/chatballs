import { fmt, t } from "../i18n";

export function initials(name: string, email: string): string {
  const source = name.trim() || email.split("@")[0] || "CB";
  const parts = source.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  return source.slice(0, 2).toUpperCase();
}

// Даты и числа считает общий модуль языка: список месяцев, порядок слов и
// разделители разрядов у каждого языка свои, и держать их здесь значило бы
// иметь вторую копию правил для виджета. Обёртки оставлены, чтобы не править
// две сотни мест вызова: имена те же, поведение теперь зависит от языка.

/** «2 сентября 2026 г.» / «2 September 2026». */
export function formatDate(value: string): string {
  return fmt.fullDate(value);
}

/** Подпись часового пояса со смещением: «Europe/Moscow · UTC+3» (кадр N1).
 *  Тег en-US здесь не язык интерфейса, а формат смещения: строка «GMT+03:00»
 *  разбирается регуляркой, и локаль подобрана под неё, а не под читателя. */
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

/** «2 сен» / «Sep 2» — короткий месяц без точки (кадры N1/N3/N6/N7). */
export function shortDate(value: string | Date): string {
  return fmt.shortDate(value);
}

/** «12 авг 2026» / «Aug 12 2026» (кадры E1/E3, G3). */
export function shortDateYear(value: string | Date): string {
  return fmt.shortDateYear(value);
}

/** «2 сен, 14:12» / «Sep 2, 14:12». */
export function shortDateTime(value: string | Date): string {
  return fmt.shortDateTime(value);
}

/** «янв 2026» — дата вступления в организацию в шапке «Профиля» (кадр P1). */
export function monthYear(value: string | Date): string {
  return fmt.monthYear(value);
}

/** «1,4 МБ» / «1.4 MB» — размер файла на языке интерфейса.
 *  Ниже мегабайта округляется до килобайт: доли килобайта в интерфейсе
 *  не нужны, а «0,3 КБ» рядом с именем файла читается хуже, чем «1 КБ». */
export function readableSize(bytes: number): string {
  const { value, unit } = fmt.bytes(bytes);
  return t(unit === "mb" ? "unit.mb" : "unit.kb", { value });
}

// Даты, числа и размеры на языке интерфейса.
//
// Почти всё делает Intl, но не всё. Дизайн-базлайн пишет короткий месяц без
// точки — «2 сен, 14:12», — а Intl на русском даёт «2 сент.»; в английском той
// же строке нужен другой порядок слов и другой список месяцев. Поэтому список
// месяцев задан явно на каждый язык, а не собран из Intl и подрезан регуляркой.
//
// Русский месяц стоит после числа и потому в родительном падеже: «2 мая», а не
// «2 май». Отдельного списка для «мая» без числа не нужно — там, где месяц
// стоит один («май 2026»), продукт его не показывает.

export type ByteUnitKey = "kb" | "mb";

type LocaleData = {
  /** Тег для Intl: он же уходит в NumberFormat и DateTimeFormat. */
  tag: string;
  /** Короткий месяц без точки, в форме «2 <месяца>». */
  shortMonths: readonly string[];
  /** «2 сен, 14:12» против «Sep 2, 14:12» — порядок задаёт язык. */
  dayMonth: (day: number, month: string) => string;
};

const LOCALES: Record<string, LocaleData> = {
  ru: {
    tag: "ru-RU",
    shortMonths: ["янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"],
    dayMonth: (day, month) => `${day} ${month}`,
  },
  en: {
    tag: "en-GB",
    shortMonths: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    dayMonth: (day, month) => `${month} ${day}`,
  },
};

const FALLBACK = LOCALES.ru;

function localeOf(language: string): LocaleData {
  return LOCALES[language] ?? FALLBACK;
}

function asDate(value: string | Date): Date | null {
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

export type Formats = {
  /** Тег Intl текущего языка: для случаев, где нужен свой форматтер. */
  tag: () => string;
  /** «2 сен» / «Sep 2» — день и короткий месяц. */
  shortDate: (value: string | Date) => string;
  /** «2 сен 2026» / «Sep 2 2026». */
  shortDateYear: (value: string | Date) => string;
  /** «2 сен, 14:12» / «Sep 2, 14:12». */
  shortDateTime: (value: string | Date) => string;
  /** «2 сентября 2026 г.» / «2 September 2026» — Intl целиком. */
  fullDate: (value: string | Date) => string;
  /** «сен 2026» / «Sep 2026». */
  monthYear: (value: string | Date) => string;
  /** «14:12». */
  time: (value: string | Date) => string;
  /** Разделители разрядов по языку: «1 250» / «1,250». */
  number: (value: number, options?: Intl.NumberFormatOptions) => string;
  /** Размер файла: возвращает число и ключ единицы — саму единицу переводит словарь. */
  bytes: (bytes: number) => { value: string; unit: ByteUnitKey };
};

export function createFormats(language: () => string): Formats {
  const locale = () => localeOf(language());

  const shortDate: Formats["shortDate"] = (value) => {
    const date = asDate(value);
    if (!date) return "";
    const data = locale();
    return data.dayMonth(date.getDate(), data.shortMonths[date.getMonth()]);
  };

  return {
    tag: () => locale().tag,
    shortDate,
    shortDateYear(value) {
      const date = asDate(value);
      return date ? `${shortDate(date)} ${date.getFullYear()}` : "";
    },
    shortDateTime(value) {
      const date = asDate(value);
      if (!date) return "";
      return `${shortDate(date)}, ${this.time(date)}`;
    },
    fullDate(value) {
      const date = asDate(value);
      if (!date) return "";
      return new Intl.DateTimeFormat(locale().tag, { day: "numeric", month: "long", year: "numeric" }).format(date);
    },
    monthYear(value) {
      const date = asDate(value);
      if (!date) return "";
      return `${locale().shortMonths[date.getMonth()]} ${date.getFullYear()}`;
    },
    time(value) {
      const date = asDate(value);
      if (!date) return "";
      return new Intl.DateTimeFormat(locale().tag, { hour: "2-digit", minute: "2-digit" }).format(date);
    },
    number(value, options) {
      return new Intl.NumberFormat(locale().tag, options).format(value);
    },
    bytes(bytes) {
      const kilobytes = bytes / 1024;
      if (kilobytes >= 1024) {
        return { value: this.number(kilobytes / 1024, { maximumFractionDigits: 1 }), unit: "mb" };
      }
      return { value: this.number(Math.max(1, Math.round(kilobytes))), unit: "kb" };
    },
  };
}

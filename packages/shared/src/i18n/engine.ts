// Движок перевода: общий для рабочего места и виджета.
//
// Библиотеки нет намеренно. Ключи здесь проверяет компилятор: словарь — обычный
// объект, русский задаёт тип, английский обязан его повторить, и забытый
// перевод падает на `tsc`, а не всплывает по-русски у клиента через месяц.
// Плюрализация и форматы берутся из Intl, который уже есть в браузере: своё
// правило «1 диалог / 2 диалога / 5 диалогов» писать не нужно.
//
// Текущий язык живёт не в переводчике, а в общем модуле (current.ts): каталогов
// несколько — у рабочего места, у виджета, у общих компонентов звонка, — и язык
// у них обязан быть один. Переводчик его только читает.

import { currentLanguage, setCurrentLanguage } from "./current";

export type PluralCategory = "one" | "few" | "many" | "other";

/** Строка словаря: либо готовая фраза, либо формы для числа. */
export type Message = string | Partial<Record<PluralCategory, string>>;

/** Значения для подстановки в `{имя}`. */
export type Params = Record<string, string | number>;

export type Catalog<K extends string> = Record<K, Message>;

export type Translator<K extends string> = {
  /** Строка на текущем языке с подстановкой `{имя}`. */
  t: (key: K, params?: Params) => string;
  /** Строка с числом: форму выбирает язык, `{count}` подставляется сам. */
  tn: (key: K, count: number, params?: Params) => string;
  /** Язык, на котором отвечает этот переводчик (общий для всех каталогов). */
  language: () => string;
  /** Сменить язык — сразу во всех каталогах. */
  setLanguage: (language: string) => boolean;
  /** Языки, для которых есть словарь. */
  languages: () => string[];
};

export type TranslatorOptions<K extends string> = {
  catalogs: Record<string, Catalog<K>>;
  /** Язык, на котором написан исходный словарь: на него уходит фолбэк. */
  source: string;
};

function interpolate(text: string, params?: Params): string {
  if (!params) return text;
  // Подстановка идёт одним проходом по шаблону, а не последовательными
  // replace по каждому параметру: иначе значение, само содержащее «{имя}»
  // (а его пишет клиент — например, в названии диалога), подставилось бы
  // ещё раз следующим параметром.
  return text.replace(/\{(\w+)\}/g, (match, name: string) =>
    Object.prototype.hasOwnProperty.call(params, name) ? String(params[name]) : match,
  );
}

const pluralRules = new Map<string, Intl.PluralRules>();

function categoryOf(language: string, count: number): PluralCategory {
  let rules = pluralRules.get(language);
  if (!rules) {
    rules = new Intl.PluralRules(language);
    pluralRules.set(language, rules);
  }
  return rules.select(count) as PluralCategory;
}

export function createTranslator<K extends string>({ catalogs, source }: TranslatorOptions<K>): Translator<K> {
  // Язык, на котором словарь есть. Общий язык может быть тем, для которого
  // этого каталога не завели, — тогда работает фолбэк на исходный.
  const active = () => {
    const language = currentLanguage();
    return language && language in catalogs ? language : source;
  };

  function lookup(key: K): Message | undefined {
    const table = catalogs[active()];
    if (table && key in table) return table[key];
    const fallback = catalogs[source];
    return fallback ? fallback[key] : undefined;
  }

  return {
    // Неизвестный ключ возвращается как есть: опечатка должна быть видна в
    // интерфейсе, но не должна ронять экран пустой строкой или исключением.
    t(key, params) {
      const message = lookup(key);
      if (message === undefined) return key;
      if (typeof message === "string") return interpolate(message, params);
      return interpolate(message.other ?? key, params);
    },
    tn(key, count, params) {
      const message = lookup(key);
      if (message === undefined) return key;
      const merged = { count, ...params };
      if (typeof message === "string") return interpolate(message, merged);
      const form = message[categoryOf(active(), count)] ?? message.other;
      return form === undefined ? key : interpolate(form, merged);
    },
    language: active,
    setLanguage: setCurrentLanguage,
    languages: () => Object.keys(catalogs),
  };
}

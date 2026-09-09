// Язык рабочего места.
//
// Язык не хук и не контекст: он живёт в модуле, и `t` импортируется в файл так
// же, как любая другая функция. Причина — цена альтернативы: провайдер и хук
// в двухстах сорока файлах ради настройки, которую меняют раз в год.
//
// Из этого следует главное правило модуля: **язык выбирается один раз, при
// инициализации**. В коде десятки констант уровня модуля — списки разделов,
// подписи ролей, наборы кнопок редактора, — и они вычисляются в момент импорта
// своего файла. Этот модуль импортируется ими же, а значит выполняется раньше
// любого из них: к тому времени, как посчитается первая такая константа, язык
// уже стоит правильный. Ставить его позже, из App, было бы поздно — половина
// подписей уже застыла бы на языке по умолчанию.
//
// Отсюда же и перезагрузка при смене языка: пересчитать застывшие константы
// нельзя, а переключают язык осознанно и редко — «Сохранить» в профиле и так
// уходит на сервер, лишняя секунда на перезагрузку там незаметна.
//
// До входа язык брать неоткуда, кроме как из прошлого визита и настроек
// браузера: логин и сброс пароля открываются до того, как известно, кто
// пришёл. Запомненный язык живёт в localStorage; после входа сессия приносит
// разрешённый сервером язык, и если он другой — страница перезагружается.

import { createI18n, resolveLanguage, normalizeLanguage, type LanguageCode } from "@chatballs/shared";

import { en } from "./en";
import { ru, type MessageKey } from "./ru";

const STORAGE_KEY = "chatballs.language";

function remembered(): LanguageCode | "" {
  try {
    return normalizeLanguage(window.localStorage.getItem(STORAGE_KEY));
  } catch {
    // Приватное окно или заблокированные куки: язык просто не запомнится.
    return "";
  }
}

function remember(code: LanguageCode): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, code);
  } catch {
    // Не запомнили — не беда: следующий вход возьмёт язык из сессии.
  }
}

const initial = resolveLanguage({ user: remembered() });

const i18n = createI18n<MessageKey>({ catalogs: { ru, en }, source: "ru" });
i18n.setLanguage(initial);
if (typeof document !== "undefined") document.documentElement.lang = initial;

export type { MessageKey };
export const t = i18n.t;
export const tn = i18n.tn;
export const fmt = i18n.fmt;
export const language = i18n.language;

/**
 * Принять язык, разрешённый сервером по цепочке профиль → организация →
 * установка. Если он отличается от текущего, страница перезагружается: часть
 * подписей уже посчитана константами модулей, и иначе экран остался бы
 * наполовину на старом языке.
 *
 * Вызывается и после загрузки сессии, и после сохранения языка в профиле —
 * в обоих случаях источник один и тот же, ответ сервера.
 */
export function acceptServerLanguage(code: string | null | undefined): void {
  const next = normalizeLanguage(code);
  if (!next || next === i18n.language()) return;
  remember(next);
  window.location.reload();
}

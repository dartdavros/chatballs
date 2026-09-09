// Текущий язык — один на весь фронтенд.
//
// Каталогов несколько: свой у рабочего места, свой у виджета, свой у общих
// компонентов звонка в packages/ui. Язык у них обязан быть общий, иначе кнопка
// «Завершить» в звонке осталась бы русской в английском интерфейсе — её текст
// живёт в другом пакете. Поэтому текущий язык держится здесь, а каждый
// переводчик только читает его.

let current = "";
const listeners = new Set<(language: string) => void>();

/** Текущий язык. Пустая строка означает «ещё не выбран». */
export function currentLanguage(): string {
  return current;
}

/**
 * Поставить язык для всех каталогов сразу.
 * Возвращает true, если он действительно поменялся.
 */
export function setCurrentLanguage(language: string): boolean {
  if (!language || language === current) return false;
  current = language;
  for (const listener of listeners) listener(language);
  return true;
}

/** Подписка на смену языка — для того, что нельзя пересчитать рендером. */
export function onLanguageChange(listener: (language: string) => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

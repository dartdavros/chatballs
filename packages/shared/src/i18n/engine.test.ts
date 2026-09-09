import { beforeEach, describe, expect, it } from "vitest";

import { setCurrentLanguage } from "./current";
import { createTranslator } from "./engine";
import { createFormats } from "./formats";

const catalogs = {
  ru: {
    "greet": "Привет, {name}",
    "count": { one: "{count} диалог", few: "{count} диалога", many: "{count} диалогов" },
    "only_ru": "Только по-русски",
  },
  en: {
    "greet": "Hello, {name}",
    "count": { one: "{count} conversation", other: "{count} conversations" },
    "only_ru": "Russian only",
  },
};

const t = createTranslator<keyof typeof catalogs.ru>({ catalogs, source: "ru" });

describe("переводчик", () => {
  beforeEach(() => {
    setCurrentLanguage("ru");
  });

  it("подставляет параметры", () => {
    expect(t.t("greet", { name: "Анна" })).toBe("Привет, Анна");
  });

  it("не подставляет параметр повторно из значения другого", () => {
    // Значение пишет клиент — например, в названии диалога. Второй проход по
    // уже подставленному тексту дал бы подстановку внутри данных.
    expect(t.t("greet", { name: "{name}" })).toBe("Привет, {name}");
  });

  it("выбирает русскую форму числа по правилам языка", () => {
    expect(t.tn("count", 1)).toBe("1 диалог");
    expect(t.tn("count", 2)).toBe("2 диалога");
    expect(t.tn("count", 5)).toBe("5 диалогов");
    expect(t.tn("count", 21)).toBe("21 диалог");
  });

  it("выбирает английскую форму числа", () => {
    setCurrentLanguage("en");
    expect(t.tn("count", 1)).toBe("1 conversation");
    expect(t.tn("count", 5)).toBe("5 conversations");
  });

  it("возвращает сам ключ, когда его нет в словаре", () => {
    // Опечатка должна быть видна на экране, но не ронять его.
    expect(t.t("нет такого" as keyof typeof catalogs.ru)).toBe("нет такого");
  });

  it("падает на язык-оригинал, если словаря для текущего языка нет", () => {
    setCurrentLanguage("de");
    expect(t.t("only_ru")).toBe("Только по-русски");
  });
});

describe("форматы", () => {
  const fmt = createFormats(t.language);

  it("пишет короткий месяц без точки на языке интерфейса", () => {
    setCurrentLanguage("ru");
    expect(fmt.shortDate("2026-09-02T10:00:00Z")).toBe("2 сен");
    setCurrentLanguage("en");
    expect(fmt.shortDate("2026-09-02T10:00:00Z")).toBe("Sep 2");
  });

  it("отдаёт размер числом и ключом единицы", () => {
    setCurrentLanguage("en");
    expect(fmt.bytes(2048)).toEqual({ value: "2", unit: "kb" });
    expect(fmt.bytes(3 * 1024 * 1024)).toEqual({ value: "3", unit: "mb" });
  });
});

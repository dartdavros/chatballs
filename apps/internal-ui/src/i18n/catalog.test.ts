import { describe, expect, it } from "vitest";

import { en } from "./en";
import { ru } from "./ru";

// Совпадение наборов ключей проверяет компилятор: en типизирован по ru, и
// пропущенный перевод — ошибка сборки. А вот параметры фразы он не сверяет:
// «{count} из {total}» и «{count} of {tota1}» для него одинаково валидны, и
// разъехавшаяся подстановка выдала бы на экране «{tota1}» вместо числа.

const PLACEHOLDER = /\{(\w+)\}/g;

function names(message: unknown): Set<string> {
  const forms = typeof message === "string" ? [message] : Object.values(message as Record<string, string>);
  return new Set(forms.flatMap((form) => [...form.matchAll(PLACEHOLDER)].map((match) => match[1])));
}

describe("словарь рабочего места", () => {
  it("держит одинаковые параметры в обоих языках", () => {
    const mismatched: string[] = [];
    for (const [key, russian] of Object.entries(ru)) {
      const left = [...names(russian)].sort().join(",");
      const right = [...names(en[key as keyof typeof ru])].sort().join(",");
      if (left !== right) mismatched.push(`${key}: «${left}» ≠ «${right}»`);
    }
    expect(mismatched).toEqual([]);
  });

  it("не оставляет пустых строк", () => {
    const empty = Object.entries(en).filter(([, value]) => typeof value === "string" && !value.trim());
    expect(empty).toEqual([]);
  });

  it("держит одинаковый набор форм числа", () => {
    const mismatched: string[] = [];
    for (const [key, russian] of Object.entries(ru)) {
      const english = en[key as keyof typeof ru];
      if (typeof russian !== typeof english) mismatched.push(key);
    }
    expect(mismatched).toEqual([]);
  });
});

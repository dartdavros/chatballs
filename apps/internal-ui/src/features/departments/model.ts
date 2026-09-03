import type { Icon } from "../../shared/icons";
import type { RouteKey } from "../../types";

type IconName = Parameters<typeof Icon>[0]["name"];

export type DepartmentCopy = {
  icon: IconName;
  description: string;
  overview: RouteKey | null;
  statLabels: [string, string, string];
};

/** Тексты и переход карточки отдела. Отдел без своей записи получает нейтральную. */
const COPY: Record<string, DepartmentCopy> = {
  sales: {
    icon: "shop",
    description: "Публичные входящие обращения новых клиентов.",
    overview: "salesDialogs",
    statLabels: ["Открытые диалоги", "Ожидают оператора", "Обслуживаются AI"],
  },
  support: {
    icon: "wrench",
    description: "Обслуживание существующих клиентов продуктов через авторизованный чат.",
    overview: "supportOverview",
    statLabels: ["Открытые обращения", "Ожидают оператора", "Обслуживаются AI"],
  },
};

const FALLBACK: DepartmentCopy = {
  icon: "building",
  description: "Отдел компании.",
  overview: null,
  statLabels: ["Открытые диалоги", "Сотрудники", "AI-агенты"],
};

export function departmentCopy(code: string): DepartmentCopy {
  return COPY[code] ?? FALLBACK;
}

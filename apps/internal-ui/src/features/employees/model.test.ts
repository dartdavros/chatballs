import { describe, expect, it } from "vitest";

import type { Employee } from "../../types";
import { filterEmployees, groupsLabel, roleAccessLabel } from "./model";

const baseEmployee: Employee = {
  id: 1,
  email: "employee@example.test",
  fullName: "Анна Котова",
  role: "EMPLOYEE",
  positionTitle: "Оператор",
  phone: "",
  groups: [{ id: 10, name: "Операторы" }],
  isActive: true,
  isBlocked: false,
  mustChangePassword: false,
  totpRequired: false,
  totpEnabled: false,
};

describe("employee list model", () => {
  it("combines role, group and text filters", () => {
    const owner = { ...baseEmployee, id: 2, email: "owner@example.test", fullName: "Иван Петров", role: "OWNER" as const, groups: [] };
    expect(filterEmployees([baseEmployee, owner], "EMPLOYEE", 10, "оператор")).toEqual([baseEmployee]);
    expect(filterEmployees([baseEmployee, owner], "OWNER", "all", "owner@")).toEqual([owner]);
    expect(filterEmployees([baseEmployee, owner], "all", 99, "")).toEqual([]);
  });

  it("labels groups and role-based access", () => {
    expect(groupsLabel(baseEmployee)).toBe("Операторы");
    expect(groupsLabel({ ...baseEmployee, groups: [] })).toBe("Без группы");
    expect(roleAccessLabel(baseEmployee)).toBe("Только чат");
    expect(roleAccessLabel({ ...baseEmployee, role: "ADMIN" })).toBe("Полный доступ");
    expect(roleAccessLabel({ ...baseEmployee, role: "OWNER" })).toBe("Полный доступ");
  });
});

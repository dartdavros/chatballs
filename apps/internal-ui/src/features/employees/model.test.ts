import { describe, expect, it } from "vitest";

import type { Employee } from "../../types";
import { groupsLabel, roleAccessLabel } from "./model";

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
  it("labels groups and role-based access", () => {
    expect(groupsLabel(baseEmployee)).toBe("Операторы");
    expect(groupsLabel({ ...baseEmployee, groups: [] })).toBe("Без группы");
    expect(roleAccessLabel(baseEmployee)).toBe("Только чат");
    expect(roleAccessLabel({ ...baseEmployee, role: "ADMIN" })).toBe("Полный доступ");
    expect(roleAccessLabel({ ...baseEmployee, role: "OWNER" })).toBe("Полный доступ");
  });
});

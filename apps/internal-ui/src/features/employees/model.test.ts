import { describe, expect, it } from "vitest";

import type { CapabilityDefinition, Employee } from "../../types";
import { groupCapabilities } from "./access-model";
import { employeeAccessLabel, filterEmployees } from "./model";

const baseEmployee: Employee = {
  id: 1,
  email: "employee@example.test",
  fullName: "Анна Котова",
  role: "EMPLOYEE",
  positionTitle: "Менеджер",
  phone: "",
  department: "sales",
  departmentName: "Продажи",
  isActive: true,
  isBlocked: false,
  mustChangePassword: false,
  totpRequired: false,
  totpEnabled: false,
  accessAssignments: [],
};

describe("employee list model", () => {
  it("combines role, placement and text filters", () => {
    const owner = { ...baseEmployee, id: 2, email: "owner@example.test", fullName: "Иван Петров", role: "OWNER" as const, department: null };
    expect(filterEmployees([baseEmployee, owner], "EMPLOYEE", "department", "менеджер")).toEqual([baseEmployee]);
    expect(filterEmployees([baseEmployee, owner], "OWNER", "company", "owner@")).toEqual([owner]);
  });

  it("does not infer employee access from role or department", () => {
    expect(employeeAccessLabel(baseEmployee)).toBe("Нет доступа");
    expect(employeeAccessLabel({ ...baseEmployee, accessAssignments: [{
      id: 3,
      profileId: 4,
      profileName: "Продажи",
      scopeType: "DEPARTMENT",
      departmentId: 1,
      departmentCode: "sales",
    }] })).toBe("1 профиль");
  });
});

describe("access catalog model", () => {
  it("keeps protected ownership capabilities in the employee domain", () => {
    const capabilities: CapabilityDefinition[] = [{
      code: "ownership.transfer",
      name: "Передача владения",
      description: "",
      allowedScopes: ["ORGANIZATION"],
      assignable: false,
      protected: true,
    }];
    const groups = groupCapabilities(capabilities);
    expect(groups[0].domain).toBe("Сотрудники");
    expect(groups[0].capabilities[0].protected).toBe(true);
  });
});

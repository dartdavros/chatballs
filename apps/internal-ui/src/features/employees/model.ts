import type { Employee, Role } from "../../types";

export type EmployeeStatus = "active" | "blocked" | "invited";
export type EmployeeRoleFilter = "all" | Role;
export type EmployeeStatusFilter = "all" | EmployeeStatus;

export type EmployeeForm = {
  department: string;
  email: string;
  fullName: string;
  phone: string;
  role: Role;
  totpEnabled: boolean;
};

export function employeeStatusKey(employee: Employee): EmployeeStatus {
  if (employee.isBlocked) return "blocked";
  if (employee.mustChangePassword) return "invited";
  return "active";
}

export function filterEmployees(employees: Employee[], role: EmployeeRoleFilter, status: EmployeeStatusFilter, query: string) {
  const q = query.trim().toLowerCase();
  return employees.filter((employee) => {
    const employeeStatus = employeeStatusKey(employee);
    return (
      (role === "all" || employee.role === role) &&
      (status === "all" || employeeStatus === status) &&
      (!q || employee.fullName.toLowerCase().includes(q) || employee.email.toLowerCase().includes(q))
    );
  });
}

export function employeeForm(employee: Employee): EmployeeForm {
  return {
    fullName: employee.fullName || employee.email,
    phone: employee.phone || employeeDetails(employee).phone,
    email: employee.email,
    role: employee.role,
    department: employee.department ?? "sales",
    totpEnabled: employee.totpEnabled,
  };
}

export function employeeDetails(employee: Employee) {
  if (employee.email === "a.kotova@edevs.tech") {
    return {
      phone: employee.phone || "+7 916 245 14 02",
      departmentLabel: employee.department === "sales" ? "Отдел продаж" : "—",
      account: {
        createdAt: "12 мая 2026",
        inviteAcceptedAt: "12 мая 2026",
        lastLogin: "5 мин назад",
      },
      security: {
        passwordChangedAt: "28 мая 2026",
        sessions: "2 устройства · Chrome (Москва), Safari (Москва)",
      },
      workload: {
        activeDialogs: 3,
        queue: 0,
        salesToday: 5,
        avgReply: "1м 40с",
      },
      activity: [
        { dot: "#52c41a", text: "Закрыла диалог · продажа Foxray", time: "8 мин назад" },
        { dot: "#1677ff", text: "Забрала диалог из очереди", time: "22 мин назад" },
        { dot: "#bfbfbf", text: "Вход в систему · Chrome", time: "сегодня 09:02" },
      ],
    };
  }
  return {
    phone: "",
    departmentLabel: employee.department === "sales" ? "Отдел продаж" : "—",
    account: {
      createdAt: "—",
      inviteAcceptedAt: "—",
      lastLogin: employee.role === "OWNER" ? "сейчас · онлайн" : "не входил",
    },
    security: {
      passwordChangedAt: "—",
      sessions: employee.role === "OWNER" ? "1 устройство · текущий браузер" : "—",
    },
    workload: {
      activeDialogs: 0,
      queue: 0,
      salesToday: 0,
      avgReply: "—",
    },
    activity: [
      { dot: "#bfbfbf", text: "Активность не зафиксирована", time: "—" },
    ],
  };
}

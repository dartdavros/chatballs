import { expect, type Page, test } from "@playwright/test";

const ORGANIZATION_PUBLIC_ID = "123e4567-e89b-12d3-a456-426614174000";
const SECOND_ORGANIZATION_PUBLIC_ID = "223e4567-e89b-12d3-a456-426614174000";

// Эти сценарии относятся только к internal-ui; на других проектах пропускаем.
test.beforeEach(({}, testInfo) => {
  test.skip(testInfo.project.name !== "internal-ui", "internal-ui only");
});

const OWNER = {
  id: 1,
  email: "owner@edevs.tech",
  fullName: "Владелец",
  role: "OWNER",
  positionTitle: "Владелец",
  organization: "edevs",
  organizationName: "Edevs",
  department: null,
  mustChangePassword: false,
  totpRequired: false,
  totpEnabled: false,
  capabilities: [
    "company.view", "departments.view", "employees.view", "employees.manage", "employees.manage_privileged", "ownership.transfer", "products.view", "ai.view",
    "ai.manage", "integrations.view", "conversations.view", "customers.view", "sales.view",
    "support.view",
  ],
  accessScopes: [{
    scopeType: "ORGANIZATION",
    departmentId: null,
    departmentCode: null,
    capabilities: [
      "company.view", "departments.view", "employees.view", "employees.manage", "employees.manage_privileged", "ownership.transfer", "products.view", "ai.view",
      "ai.manage", "integrations.view", "conversations.view", "customers.view", "sales.view",
      "support.view",
    ],
  }],
};

// «Оператор» — рабочая функция обычного сотрудника (EMPLOYEE) в отделе (ADR-HUB-0027).
const OPERATOR_CAPABILITIES = ["conversations.view", "conversations.operate", "customers.view", "sales.view", "sales.operate"];
const OPERATOR = {
  ...OWNER,
  id: 2,
  email: "operator@edevs.tech",
  fullName: "Оператор",
  role: "EMPLOYEE",
  positionTitle: "Оператор отдела продаж",
  department: "sales",
  capabilities: OPERATOR_CAPABILITIES,
  accessScopes: [{
    scopeType: "DEPARTMENT",
    departmentId: 1,
    departmentCode: "sales",
    capabilities: OPERATOR_CAPABILITIES,
  }],
};

const identityFor = (membership: typeof OWNER) => ({
  id: membership.id,
  email: membership.email,
  fullName: membership.fullName,
  mustChangePassword: membership.mustChangePassword,
  totpEnabled: membership.totpEnabled,
  memberships: [{
    id: membership.id,
    organizationPublicId: ORGANIZATION_PUBLIC_ID,
    organization: membership.organization,
    organizationName: membership.organizationName,
    role: membership.role,
    positionTitle: membership.positionTitle,
    department: membership.department,
    totpRequired: membership.totpRequired,
    capabilities: membership.capabilities,
    accessScopes: membership.accessScopes,
  }],
});

const OWNER_IDENTITY = identityFor(OWNER);
const OPERATOR_IDENTITY = identityFor(OPERATOR);

async function mockData(page: Page) {
  const permissions = {
    canView: true, canUpdateProfile: true, canChangeRole: true, canChangePlacement: true,
    canChangeAccess: true, canBlock: true, canUnblock: false, canResetPassword: true,
    canTerminateSessions: true, canTransferOwnership: false,
  };
  const employee = {
    id: 7, email: "d.sokolov@edevs.tech", fullName: "Дмитрий Соколов", phone: "+7 903 118 77 51",
    role: "EMPLOYEE", positionTitle: "Менеджер по продажам", department: "sales", departmentName: "Отдел продаж",
    createdAt: "2026-05-20T10:00:00Z", lastLogin: "2026-07-13T08:30:00Z", isActive: true, isBlocked: false,
    mustChangePassword: false, totpRequired: false, totpEnabled: true, permissions,
    accessAssignments: [{
      id: 11, profileId: 1, profileName: "Продажи · оператор", scopeType: "DEPARTMENT",
      departmentId: 1, departmentCode: "sales", departmentName: "Отдел продаж",
      capabilities: ["sales.view", "sales.operate", "customers.view", "conversations.view"],
    }],
  };
  const ownerEmployee = {
    id: 1, email: OWNER.email, fullName: OWNER.fullName, phone: "+7 916 000 11 22",
    role: "OWNER", positionTitle: OWNER.positionTitle, department: null, departmentName: null,
    createdAt: "2026-02-02T10:00:00Z", lastLogin: "2026-07-13T08:40:00Z", isActive: true, isBlocked: false,
    mustChangePassword: false, totpRequired: false, totpEnabled: true,
    permissions: { ...permissions, canChangeRole: false, canChangePlacement: false, canTransferOwnership: true },
    accessAssignments: [],
  };
  const profiles = [{
    id: 1, name: "Продажи · оператор", description: "Работа с диалогами, клиентами и продажами отдела.",
    isSystem: false, isActive: true, capabilities: ["sales.view", "sales.operate", "customers.view", "conversations.view"],
    allowedScopes: ["DEPARTMENT", "ORGANIZATION"], assignedCount: 1,
  }];
  const capabilities = [
    { code: "sales.view", name: "Просмотр продаж", description: "", allowedScopes: ["DEPARTMENT", "ORGANIZATION"], assignable: true, protected: false },
    { code: "sales.operate", name: "Работа с продажами", description: "", allowedScopes: ["DEPARTMENT", "ORGANIZATION"], assignable: true, protected: false },
    { code: "employees.manage_privileged", name: "Управление привилегированными сотрудниками", description: "", allowedScopes: ["ORGANIZATION"], assignable: false, protected: true },
    { code: "ownership.transfer", name: "Передача владения", description: "", allowedScopes: ["ORGANIZATION"], assignable: false, protected: true },
  ];
  await page.route("**/api/v1/organizations/*/access-profiles/capabilities/", (route) => route.fulfill({ json: { items: capabilities } }));
  await page.route("**/api/v1/organizations/*/access-profiles/", (route) => route.fulfill({ json: { items: profiles } }));
  await page.route("**/api/v1/organizations/*/employees/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/employees/7/")) {
      return route.fulfill({ json: { employee: { ...employee, activeSessionCount: 1, auditEvents: [{ action: "identity.employee_created", result: "SUCCESS", createdAt: "2026-05-20T10:00:00Z" }] } } });
    }
    return route.fulfill({ json: { items: [ownerEmployee, employee] } });
  });
  await page.route("**/api/v1/organizations/*/company/departments/**", (route) => route.fulfill({ json: { items: [{ id: 1, code: "sales", name: "Отдел продаж", status: "ACTIVE", memberCount: 1, operatorCount: 1, activeOperatorCount: 1, agentCount: 0, products: [] }] } }));
  await page.route("**/api/v1/organizations/*/company/products/**", (route) => route.fulfill({ json: { items: [] } }));
  await page.route("**/api/v1/organizations/*/ai/agents/**", (route) => route.fulfill({ json: { items: [] } }));
}

async function mockSession(page: Page, user: object | null) {
  await page.route("**/api/v1/auth/session/", (route) =>
    route.fulfill({ json: user ? { authenticated: true, user } : { authenticated: false } }),
  );
}

async function login(page: Page, user: object) {
  await mockSession(page, null);
  await mockData(page);
  await page.route("**/api/v1/auth/login/", (route) => route.fulfill({ json: { authenticated: true, user } }));
  await page.goto("/");
  await page.getByPlaceholder("you@edevs.tech").fill("user@edevs.tech");
  await page.getByPlaceholder("Пароль").fill("Password-123");
  await page.getByRole("button", { name: "Войти" }).click();
}

test("OWNER logs in and lands on the command center with the global sidebar", async ({ page }) => {
  await login(page, OWNER_IDENTITY);

  await expect(page).toHaveURL(new RegExp(`/organizations/${ORGANIZATION_PUBLIC_ID}/`));
  await expect(page.getByRole("heading", { name: "Командный центр" })).toBeVisible();
  // Глобальный sidebar уровня компании.
  await expect(page.getByText("Уровень компании")).toBeVisible();
  await expect(page.getByText("Рабочее пространство")).toHaveCount(0);
});

test("OPERATOR logs in and lands on sales dialogs with the sales sidebar", async ({ page }) => {
  await login(page, OPERATOR_IDENTITY);

  await expect(page).toHaveURL(/\/departments\/sales\/dialogs/);
  // Операторская навигация показывает только рабочее пространство продаж.
  await expect(page.getByText("Рабочее пространство")).toBeVisible();
  await expect(page.getByText("Уровень компании")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Назад" })).toHaveCount(0);
});

test("OPERATOR opening an owner-only route sees the 403 permission screen", async ({ page }) => {
  await mockSession(page, OPERATOR_IDENTITY);
  await mockData(page);

  await page.goto("/employees");

  await expect(page.getByText("403 · Доступ запрещён")).toBeVisible();
  await expect(page.getByRole("button", { name: "Вернуться" })).toBeVisible();
});

test("the organization URL selects one membership without a global session tenant", async ({ page }) => {
  const secondMembership = {
    ...OWNER_IDENTITY.memberships[0],
    id: 3,
    organizationPublicId: SECOND_ORGANIZATION_PUBLIC_ID,
    organization: "second",
    organizationName: "Second",
  };
  const requests: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/api/v1/organizations/")) requests.push(request.url());
  });
  await mockSession(page, {
    ...OWNER_IDENTITY,
    memberships: [...OWNER_IDENTITY.memberships, secondMembership],
  });
  await mockData(page);

  await page.goto(`/organizations/${SECOND_ORGANIZATION_PUBLIC_ID}/`);

  await expect(page.getByRole("heading", { name: "Командный центр" })).toBeVisible();
  await expect.poll(() => requests.some((url) => url.includes(SECOND_ORGANIZATION_PUBLIC_ID))).toBe(true);
});

test("internal UI renders at the minimum supported width of 1024px", async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 768 });
  await mockSession(page, OWNER_IDENTITY);
  await mockData(page);

  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Командный центр" })).toBeVisible();
  await page.screenshot({ path: "test-results/internal-ui-owner-1024.png" });
});

test("employee stage 3 screens follow the approved baseline", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 940 });
  await mockSession(page, OWNER_IDENTITY);
  await mockData(page);

  await page.goto("/employees");
  await expect(page.getByRole("heading", { name: "Сотрудники" })).toBeVisible();
  await expect(page.getByText("Дмитрий Соколов")).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "ДОСТУП" })).toBeVisible();
  await page.screenshot({ path: "test-results/employees-stage-3-list.png", fullPage: true });

  await page.getByRole("button", { name: "Добавить сотрудника" }).click();
  await expect(page.getByRole("complementary", { name: "Новый сотрудник" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "1 Учётные данные" })).toBeVisible();
  await page.screenshot({ path: "test-results/employees-stage-3-create.png", fullPage: true });
  await page.getByRole("button", { name: "Закрыть", exact: true }).click();

  await page.getByRole("button", { name: "Действия: Владелец" }).click();
  await page.getByRole("button", { name: "Передать владение" }).click();
  const transferDialog = page.getByRole("dialog", { name: "Передача владения" });
  await expect(transferDialog).toBeVisible();
  await page.screenshot({ path: "test-results/employees-stage-3-ownership.png", fullPage: true });
  await transferDialog.getByRole("button", { name: "Отмена" }).click();

  await page.getByRole("button", { name: /^Дмитрий Соколов d\.sokolov/ }).click();
  await expect(page).toHaveURL(/\/employees\/7$/);
  await expect(page.getByRole("heading", { name: "Дмитрий Соколов" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Профили доступа и scopes" })).toBeVisible();
  await page.screenshot({ path: "test-results/employees-stage-3-detail.png", fullPage: true });

  await page.getByRole("button", { name: "Все сотрудники" }).click();
  await page.getByRole("button", { name: "Профили доступа" }).click();
  await expect(page).toHaveURL(/\/employees\/access-profiles$/);
  await expect(page.getByRole("heading", { name: "Профили доступа", exact: true })).toBeVisible();
  await expect(page.getByText("Продажи · оператор").first()).toBeVisible();
  await page.screenshot({ path: "test-results/employees-stage-3-profiles.png", fullPage: true });
});

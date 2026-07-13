import { expect, type Page, test } from "@playwright/test";

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
    "company.view", "departments.view", "employees.view", "products.view", "ai.view",
    "ai.manage", "integrations.view", "conversations.view", "customers.view", "sales.view",
    "support.view",
  ],
  accessScopes: [{
    scopeType: "ORGANIZATION",
    departmentId: null,
    departmentCode: null,
    capabilities: [
      "company.view", "departments.view", "employees.view", "products.view", "ai.view",
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

async function mockData(page: Page) {
  await page.route("**/api/v1/employees/**", (route) => route.fulfill({ json: { items: [] } }));
  await page.route("**/api/v1/company/departments/**", (route) => route.fulfill({ json: { items: [] } }));
  await page.route("**/api/v1/company/products/**", (route) => route.fulfill({ json: { items: [] } }));
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
  await login(page, OWNER);

  await expect(page).toHaveURL(/\/$|\/command/);
  await expect(page.getByRole("heading", { name: "Командный центр" })).toBeVisible();
  // Глобальный sidebar уровня компании.
  await expect(page.getByText("Уровень компании")).toBeVisible();
  await expect(page.getByText("Рабочее пространство")).toHaveCount(0);
});

test("OPERATOR logs in and lands on sales dialogs with the sales sidebar", async ({ page }) => {
  await login(page, OPERATOR);

  await expect(page).toHaveURL(/\/departments\/sales\/dialogs/);
  // Операторская навигация показывает только рабочее пространство продаж.
  await expect(page.getByText("Рабочее пространство")).toBeVisible();
  await expect(page.getByText("Уровень компании")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Назад в Hub" })).toHaveCount(0);
});

test("OPERATOR opening an owner-only route sees the 403 permission screen", async ({ page }) => {
  await mockSession(page, OPERATOR);
  await mockData(page);

  await page.goto("/employees");

  await expect(page.getByText("403 · Доступ запрещён")).toBeVisible();
  await expect(page.getByRole("button", { name: "Вернуться" })).toBeVisible();
});

test("internal UI renders at the minimum supported width of 1024px", async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 768 });
  await mockSession(page, OWNER);
  await mockData(page);

  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Командный центр" })).toBeVisible();
  await page.screenshot({ path: "test-results/internal-ui-owner-1024.png" });
});

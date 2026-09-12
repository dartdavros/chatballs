import { expect, type Page, test } from "@playwright/test";

const ORGANIZATION_PUBLIC_ID = "123e4567-e89b-12d3-a456-426614174000";
const SECOND_ORGANIZATION_PUBLIC_ID = "223e4567-e89b-12d3-a456-426614174000";

// Эти сценарии относятся только к internal-ui; на других проектах пропускаем.
test.beforeEach(({}, testInfo) => {
  test.skip(testInfo.project.name !== "internal-ui", "internal-ui only");
});

// Навигация владельца и администратора — ровно эти семь пунктов
// (SPEC-CHATBALLS-0031 §4). У сотрудника навигации нет вовсе: его единственный
// экран — чат.
const MANAGER_NAV = ["Чат", "Контакты", "Агенты", "Сотрудники", "Порталы", "База знаний", "Настройки"];

// Понятия, снесённые пивотом в контакт-центр (ADR-CHATBALLS-0041) и удалением
// сущности Product (ADR-CHATBALLS-0045). Проверяем, что они не вернулись в
// интерфейс: именно их ждали прежние редакции этих тестов.
const REMOVED_FROM_UI = ["Командный центр", "Отделы", "Продажи", "Каналы", "Подключения", "Продукты"];

const GROUPS = [
  { id: 1, name: "Операторы", color: "#1677ff", memberCount: 1, memberIds: [7], createdAt: "2026-02-02T10:00:00Z" },
  { id: 2, name: "Поддержка", color: "#2aa876", memberCount: 0, memberIds: [], createdAt: "2026-02-02T10:00:00Z" },
];

type Role = "OWNER" | "ADMIN" | "EMPLOYEE";

// Права выводятся только из роли (ADR-CHATBALLS-0041 §5). Каталог — зеркало
// backend'а, `chatballs/identity/capabilities.py`: OWNER получает всё, ADMIN —
// всё, кроме передачи владения, EMPLOYEE — фиксированный набор для чата.
const OWNER_ONLY_CAPABILITIES = ["ownership.transfer"];
const EMPLOYEE_CAPABILITIES = [
  "conversations.view", "conversations.operate", "conversations.call",
  "customers.view", "support.view", "support.operate",
];
const ALL_CAPABILITIES = [
  "ai.manage", "ai.publish", "ai.view", "audit.view", "channels.manage", "channels.view",
  "company.manage", "company.view", "conversations.call", "conversations.operate",
  "conversations.view", "customers.manage", "customers.view", "employees.manage",
  "employees.manage_privileged", "employees.view", "groups.manage", "integrations.manage",
  "integrations.view", "notifications.manage", "ownership.transfer", "secrets.manage",
  "settings.manage", "settings.view", "support.operate", "support.view",
];

function capabilitiesFor(role: Role): string[] {
  if (role === "EMPLOYEE") return EMPLOYEE_CAPABILITIES;
  if (role === "ADMIN") return ALL_CAPABILITIES.filter((item) => !OWNER_ONLY_CAPABILITIES.includes(item));
  return ALL_CAPABILITIES;
}

function membershipFor(role: Role, overrides: Record<string, unknown> = {}) {
  return {
    id: 1,
    organizationPublicId: ORGANIZATION_PUBLIC_ID,
    organization: "atelier-nord",
    organizationName: "Ателье Норд",
    organizationLogoUrl: null,
    role,
    positionTitle: role === "EMPLOYEE" ? "Оператор" : "Владелец",
    totpRequired: false,
    capabilities: capabilitiesFor(role),
    groups: role === "EMPLOYEE" ? [{ id: 1, name: "Операторы" }] : [],
    joinedAt: "2026-02-02T10:00:00Z",
    ...overrides,
  };
}

function identityFor(role: Role, memberships = [membershipFor(role)]) {
  return {
    id: role === "EMPLOYEE" ? 7 : 1,
    email: role === "EMPLOYEE" ? "operator@example.com" : "owner@example.com",
    fullName: role === "EMPLOYEE" ? "Светлана Петрова" : "Елена Кузнецова",
    avatarUrl: null,
    mustChangePassword: false,
    totpEnabled: false,
    totpLastUsedAt: null,
    deliveryMode: "SELF_HOSTED",
    isInstanceAdmin: role === "OWNER",
    // Язык отдаёт сервер: без него интерфейс открылся бы на языке браузера.
    language: "ru",
    uiLanguage: "",
    memberships,
    uiTheme: "LIGHT",
    uiAccent: "#1677ff",
  };
}

const OWNER_IDENTITY = identityFor("OWNER");
const EMPLOYEE_IDENTITY = identityFor("EMPLOYEE");

const EMPLOYEE_PERMISSIONS = {
  canView: true,
  canUpdateProfile: true,
  canChangeRole: true,
  canChangeGroups: true,
  canBlock: true,
  canUnblock: false,
  canResetPassword: true,
  canTerminateSessions: true,
  canTransferOwnership: false,
};

const STAFF = {
  id: 7,
  email: "s.petrova@example.com",
  fullName: "Светлана Петрова",
  avatarUrl: null,
  role: "EMPLOYEE",
  positionTitle: "Оператор",
  phone: "+7 903 118 77 51",
  groups: [{ id: 1, name: "Операторы" }],
  createdAt: "2026-05-20T10:00:00Z",
  lastLogin: "2026-09-01T08:30:00Z",
  isActive: true,
  isBlocked: false,
  mustChangePassword: false,
  totpRequired: false,
  totpEnabled: true,
  permissions: EMPLOYEE_PERMISSIONS,
};

// Администратор нужен списку кандидатов на передачу владения: без него диалог
// показывает пустое состояние, и проверять в нём нечего.
const ADMIN_STAFF = {
  ...STAFF,
  id: 4,
  email: "a.kim@example.com",
  fullName: "Анна Ким",
  role: "ADMIN",
  positionTitle: "Администратор",
  groups: [],
};

const OWNER_STAFF = {
  ...STAFF,
  id: 1,
  email: "owner@example.com",
  fullName: "Елена Кузнецова",
  role: "OWNER",
  positionTitle: "Владелец",
  groups: [],
  // Владельца нельзя удалить и заблокировать; единственное опасное действие на
  // его карточке — передача владения (SPEC-CHATBALLS-0031 §3).
  permissions: { ...EMPLOYEE_PERMISSIONS, canBlock: false, canChangeRole: false, canTransferOwnership: true },
};

// Пустое, но валидное окружение экрана: чат, справочники и чек-лист запуска.
// Без него любой экран падает в состояние ошибки и проверять на нём нечего.
// Ожидающее приглашение существующей учётной записи: строка со статусом
// «Приглашён» перед сотрудниками (кадры E1/E2).
const INVITATION = {
  id: 9,
  email: "guest@example.com",
  fullName: "Пётр Приглашённый",
  avatarUrl: null,
  role: "EMPLOYEE",
  positionTitle: "Оператор поддержки",
  phone: "",
  groups: [{ id: 1, name: "Операторы" }],
  invitedAt: "2026-09-10T10:00:00Z",
  expiresAt: "2026-09-17T10:00:00Z",
};

async function mockInstance(page: Page) {
  await page.route("**/api/v1/setup/", (route) => route.fulfill({ json: { needsSetup: false } }));
  await page.route("**/api/v1/instance/**", (route) => route.fulfill({ json: {} }));
  await page.route("**/api/v1/organizations/*/conversations/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/conversations/counters/")) {
      return route.fulfill({ json: { all: 0, waiting: 0, mine: 0, ungrouped: 0, groups: [], agents: [], assignees: [] } });
    }
    if (path.endsWith("/conversations/directory/")) {
      return route.fulfill({ json: { groups: GROUPS.map((group) => ({ id: group.id, name: group.name, color: group.color })), employees: [] } });
    }
    if (path.endsWith("/conversations/stats/")) return route.fulfill({ json: { waiting: 0 } });
    return route.fulfill({ json: { items: [] } });
  });
  await page.route("**/api/v1/organizations/*/company/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/company/launch-checklist/")) {
      return route.fulfill({ json: { agentCreated: true, connectionBound: true, employeeInvited: true, done: true } });
    }
    return route.fulfill({ json: { items: GROUPS } });
  });
  await page.route("**/api/v1/organizations/*/agents/**", (route) => route.fulfill({ json: { items: [], page: 1, pageSize: 20, total: 0, pageCount: 1 } }));
  await page.route("**/api/v1/organizations/*/notifications/**", (route) => route.fulfill({ json: { items: [] } }));
}

async function mockEmployees(page: Page) {
  await page.route("**/api/v1/organizations/*/employees/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    const detail = path.match(/\/employees\/(\d+)\/$/);
    if (detail) {
      const employee = { "1": OWNER_STAFF, "4": ADMIN_STAFF }[detail[1]] ?? STAFF;
      return route.fulfill({
        json: {
          employee: {
            ...employee,
            activeSessionCount: 1,
            passwordChangedAt: "2026-08-01T10:00:00Z",
            auditEvents: [{ action: "identity.employee_created", result: "SUCCESS", createdAt: "2026-05-20T10:00:00Z" }],
          },
        },
      });
    }
    // Список сотрудников постраничный, роль и поиск отбирает сервер — мок
    // повторяет этот контракт, иначе он проверял бы несуществующее поведение.
    const params = new URL(route.request().url()).searchParams;
    const role = params.get("role");
    const query = (params.get("q") ?? "").toLowerCase();
    const items = [OWNER_STAFF, ADMIN_STAFF, STAFF]
      .filter((employee) => !role || employee.role === role)
      .filter((employee) => !query || `${employee.fullName} ${employee.email} ${employee.positionTitle}`.toLowerCase().includes(query));
    return route.fulfill({
      json: { items, page: 1, pageSize: 20, total: items.length, pageCount: 1, invitations: [INVITATION] },
    });
  });
}

async function mockSession(page: Page, user: object | null) {
  await page.route("**/api/v1/auth/session/", (route) =>
    route.fulfill({ json: user ? { authenticated: true, user } : { authenticated: false, language: "ru" } }),
  );
}

async function login(page: Page, user: object) {
  await mockSession(page, null);
  await mockInstance(page);
  await mockEmployees(page);
  await page.route("**/api/v1/auth/login/", (route) => route.fulfill({ json: { authenticated: true, user } }));
  await page.goto("/");
  await page.getByPlaceholder("you@domain.ru").fill("user@example.com");
  await page.getByPlaceholder("Пароль").fill("Password-123");
  await page.getByRole("button", { name: "Войти" }).click();
}

const managerNav = (page: Page) => page.locator("nav.hub-nav button.hub-nav-item");

test("владелец после входа попадает в чат и видит семь пунктов навигации", async ({ page }) => {
  await login(page, OWNER_IDENTITY);

  await expect(page).toHaveURL(new RegExp(`/organizations/${ORGANIZATION_PUBLIC_ID}/chat`));
  await expect(managerNav(page)).toHaveCount(MANAGER_NAV.length);
  for (const label of MANAGER_NAV) {
    await expect(page.locator("nav.hub-nav").getByRole("button", { name: label, exact: true })).toBeVisible();
  }
  for (const removed of REMOVED_FROM_UI) {
    await expect(page.getByRole("button", { name: removed, exact: true })).toHaveCount(0);
  }
});

test("сотрудник после входа попадает в чат, и навигации у него нет", async ({ page }) => {
  await login(page, EMPLOYEE_IDENTITY);

  await expect(page).toHaveURL(new RegExp(`/organizations/${ORGANIZATION_PUBLIC_ID}/chat`));
  await expect(page.locator(".sales-conversation-empty")).toBeVisible();
  // Единственный экран сотрудника: сайдбар сведён к дереву диалогов, пунктов
  // администрирования нет ни одного. Дерево тоже лежит в nav.hub-nav, поэтому
  // проверяем именно пункты навигации.
  await expect(page.locator("nav.chat-scope-tree")).toBeVisible();
  await expect(managerNav(page)).toHaveCount(0);
  for (const label of MANAGER_NAV.filter((item) => item !== "Чат")) {
    await expect(page.getByRole("button", { name: label, exact: true })).toHaveCount(0);
  }
});

test("сотрудник на менеджерском маршруте видит экран 403", async ({ page }) => {
  await mockSession(page, EMPLOYEE_IDENTITY);
  await mockInstance(page);
  await mockEmployees(page);

  await page.goto("/employees");

  await expect(page.getByText("403 · Доступ запрещён")).toBeVisible();
  await expect(page.getByRole("button", { name: "Вернуться" })).toBeVisible();
});

test("организация выбирается адресом, а не сохранённой сессией", async ({ page }) => {
  const secondMembership = membershipFor("OWNER", {
    id: 3,
    organizationPublicId: SECOND_ORGANIZATION_PUBLIC_ID,
    organization: "second",
    organizationName: "Вторая организация",
  });
  const requests: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/api/v1/organizations/")) requests.push(request.url());
  });
  await mockInstance(page);
  await mockEmployees(page);
  await mockSession(page, identityFor("OWNER", [membershipFor("OWNER"), secondMembership]));

  await page.goto(`/organizations/${SECOND_ORGANIZATION_PUBLIC_ID}/`);

  await expect(managerNav(page)).toHaveCount(MANAGER_NAV.length);
  // Организация берётся из адреса: запросы уходят только во вторую организацию,
  // хотя членство в первой тоже есть.
  await expect.poll(() => requests.some((url) => url.includes(SECOND_ORGANIZATION_PUBLIC_ID))).toBe(true);
  expect(requests.filter((url) => url.includes(ORGANIZATION_PUBLIC_ID))).toEqual([]);
});

test("ожидающее приглашение показано строкой «Приглашён» с меню отправки и отзыва", async ({ page }) => {
  await mockSession(page, OWNER_IDENTITY);
  await mockInstance(page);
  await mockEmployees(page);
  const posted: string[] = [];
  await page.route("**/api/v1/organizations/*/employees/invitations/**", (route) => {
    posted.push(new URL(route.request().url()).pathname);
    return route.fulfill({ json: { ok: true } });
  });

  await page.goto(`/organizations/${ORGANIZATION_PUBLIC_ID}/employees`);

  const row = page.locator(".employees-row.is-invited");
  await expect(row).toHaveCount(1);
  await expect(row.getByText("Пётр Приглашённый")).toBeVisible();
  await expect(row.locator(".employees-badge.has-dot")).toHaveText("Приглашён");
  await expect(row.getByText("Оператор поддержки")).toBeVisible();

  await row.locator(".employees-row-menu").click();
  await page.getByRole("button", { name: "Отправить приглашение ещё раз" }).click();
  await expect.poll(() => posted).toContain(`/api/v1/organizations/${ORGANIZATION_PUBLIC_ID}/employees/invitations/9/resend/`);
});

test("гость по ссылке-приглашению задаёт имя и пароль и попадает в организацию", async ({ page }) => {
  await mockSession(page, null);
  await mockInstance(page);
  await mockEmployees(page);
  await page.route("**/api/v1/auth/invitations/preview/**", (route) =>
    route.fulfill({ json: { valid: true, email: "new-owner@example.com", organizationName: "Новая организация", accountExists: false } }),
  );
  const registered: string[] = [];
  await page.route("**/api/v1/auth/invitations/register/", async (route) => {
    registered.push(route.request().postData() ?? "");
    const user = identityFor("OWNER", [membershipFor("OWNER", { organizationPublicId: SECOND_ORGANIZATION_PUBLIC_ID, organization: "new", organizationName: "Новая организация" })]);
    // После регистрации сессия уже есть — сессионный мок отвечает как для вошедшего.
    await mockSession(page, user);
    return route.fulfill({ status: 201, json: { authenticated: true, user, organizationPublicId: SECOND_ORGANIZATION_PUBLIC_ID } });
  });

  await page.goto("/join?token=guest-token");

  await expect(page.getByText("Вас приглашают в «Новая организация»")).toBeVisible();
  await page.getByPlaceholder("Елена Кузнецова").fill("Новый Владелец");
  await page.getByPlaceholder("Минимум 10 символов").fill("Very-strong-passphrase-42");
  await page.getByRole("button", { name: "Принять приглашение" }).click();

  await expect(page).toHaveURL(new RegExp(`/organizations/${SECOND_ORGANIZATION_PUBLIC_ID}/`));
  await expect(managerNav(page)).toHaveCount(MANAGER_NAV.length);
  expect(registered[0]).toContain("guest-token");
});

test("администратор установки видит баннер о новой версии и запускает обновление", async ({ page }) => {
  await mockSession(page, OWNER_IDENTITY);
  await mockInstance(page);
  await mockEmployees(page);
  const update = {
    currentVersion: "1.4.0", latestVersion: "1.5.0", latestName: "v1.5.0", latestNotes: "", latestPublishedAt: null,
    latestPageUrl: "https://github.com/dartdavros/chatballs/releases/tag/v1.5.0", available: true, checkedAt: null,
    checkError: "", updaterOnline: true, install: { version: null, status: "IDLE", message: "", requestedAt: null, updatedAt: null },
  };
  await page.route("**/api/v1/instance/update/", (route) => route.fulfill({ json: { update } }));
  const installs: string[] = [];
  await page.route("**/api/v1/instance/update/install/", (route) => {
    installs.push(route.request().method());
    return route.fulfill({ status: 202, json: { update: { ...update, install: { ...update.install, version: "1.5.0", status: "REQUESTED" } } } });
  });

  await page.goto(`/organizations/${ORGANIZATION_PUBLIC_ID}/chat`);

  const banner = page.locator(".update-banner");
  await expect(banner).toContainText("Доступна версия 1.5.0");
  await banner.getByRole("button", { name: "Обновить", exact: true }).click();
  await expect(page.getByText("Обновить до 1.5.0?")).toBeVisible();
  await page.locator(".decision-dialog").getByRole("button", { name: "Обновить", exact: true }).click();

  await expect.poll(() => installs).toEqual(["POST"]);
  await expect(page.locator(".update-banner")).toContainText("Обновление до 1.5.0");
});

test("с несколькими организациями вход открывает первую, переключатель ведёт во вторую", async ({ page }) => {
  const secondMembership = membershipFor("OWNER", {
    id: 3,
    organizationPublicId: SECOND_ORGANIZATION_PUBLIC_ID,
    organization: "second",
    organizationName: "Вторая организация",
  });
  await mockInstance(page);
  await mockEmployees(page);
  await mockSession(page, identityFor("OWNER", [membershipFor("OWNER"), secondMembership]));

  // Адрес без организации: открывается первая по списку, а не экран «нет доступа».
  await page.goto("/");

  await expect(managerNav(page)).toHaveCount(MANAGER_NAV.length);
  await expect(page).toHaveURL(new RegExp(`/organizations/${ORGANIZATION_PUBLIC_ID}/`));
  await expect(page.locator(".hub-brand-switch span")).toHaveText("Ателье Норд");

  // Переключатель (A1): в списке обе организации, текущая отмечена.
  await page.locator(".hub-brand-switch").click();
  const menu = page.locator(".app-dropdown");
  await expect(menu.getByRole("button", { name: "Ателье Норд" })).toHaveClass(/is-checked/);
  await menu.getByRole("button", { name: "Вторая организация" }).click();

  await expect(page).toHaveURL(new RegExp(`/organizations/${SECOND_ORGANIZATION_PUBLIC_ID}/`));
  await expect(page.locator(".hub-brand-switch span")).toHaveText("Вторая организация");
  await expect(managerNav(page)).toHaveCount(MANAGER_NAV.length);
});

test("интерфейс работает на минимальной поддерживаемой ширине 1024px", async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 768 });
  await mockInstance(page);
  await mockEmployees(page);
  await mockSession(page, OWNER_IDENTITY);

  await page.goto("/");

  await expect(managerNav(page)).toHaveCount(MANAGER_NAV.length);
  await expect(page.locator(".sales-conversation-empty")).toBeVisible();
  // На минимальной ширине страница не должна прокручиваться по горизонтали
  // (SPEC-CHATBALLS-0031 §8).
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(0);
  await page.screenshot({ path: "test-results/internal-ui-owner-1024.png" });
});

test("экран сотрудников: список, создание, карточка и передача владения", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 940 });
  await mockInstance(page);
  await mockEmployees(page);
  await mockSession(page, OWNER_IDENTITY);

  await page.goto("/employees");
  await expect(page.getByRole("heading", { name: "Сотрудники" })).toBeVisible();
  await expect(page.getByText("Светлана Петрова").first()).toBeVisible();

  // Состав колонок текущего списка. Прежняя редакция теста искала колонку
  // «ДОСТУП» ролью columnheader — список не является семантической таблицей.
  const head = page.locator(".employees-thead");
  for (const column of ["Сотрудник", "Роль", "Должность", "Группы", "Доступ", "Статус", "Последний вход"]) {
    await expect(head.getByText(column, { exact: true })).toBeVisible();
  }
  await page.screenshot({ path: "test-results/employees-list.png", fullPage: true });

  await page.getByRole("button", { name: "Добавить сотрудника" }).click();
  await expect(page.getByRole("complementary", { name: "Новый сотрудник" })).toBeVisible();
  await page.screenshot({ path: "test-results/employees-create.png", fullPage: true });
  await page.getByRole("button", { name: "Закрыть", exact: true }).click();

  // Карточка сотрудника: должность и группы вместо прежних профилей доступа и
  // отделов.
  await page.getByRole("button", { name: /Светлана Петрова/ }).first().click();
  await expect(page).toHaveURL(/\/employees\/7$/);
  await expect(page.getByRole("heading", { name: "Светлана Петрова" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Должность и группы" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Системная роль" })).toBeVisible();
  await expect(page.getByText("Профили доступа")).toHaveCount(0);
  await page.screenshot({ path: "test-results/employees-detail.png", fullPage: true });

  // Передача владения живёт в «Опасной зоне» карточки владельца, а не в меню
  // строки списка.
  await page.getByRole("button", { name: "Все сотрудники" }).click();
  await page.getByRole("button", { name: /Елена Кузнецова/ }).first().click();
  await expect(page).toHaveURL(/\/employees\/1$/);
  await expect(page.getByRole("heading", { name: "Опасная зона" })).toBeVisible();
  await page.getByRole("button", { name: "Передать владение" }).click();
  const transferDialog = page.getByRole("dialog", { name: "Передача владения" });
  await expect(transferDialog).toBeVisible();
  // Кандидатами могут быть только активные администраторы: сотрудника в списке
  // быть не должно.
  const candidates = transferDialog.locator("select");
  await expect(candidates.locator("option")).toHaveCount(1);
  await expect(candidates.locator("option")).toContainText("Анна Ким");
  await page.screenshot({ path: "test-results/employees-ownership.png", fullPage: true });
  await transferDialog.getByRole("button", { name: "Отмена" }).click();
  await expect(transferDialog).toHaveCount(0);
});

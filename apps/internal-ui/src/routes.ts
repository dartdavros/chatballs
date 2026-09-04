import type { RouteKey } from "./types";

export const routes: Record<RouteKey, string> = {
  administrationOrganization: "Организация",
  administrationAudit: "Аудит",
  command: "Обзор",
  employeeDetail: "Сотрудники",
  employees: "Сотрудники",
  profile: "Профиль",
  settings: "Настройки",
  salesClientDetail: "Контакт",
  salesClients: "Контакты",
  chat: "Чат",
  supportOverview: "Обзор",
  supportPortals: "Порталы",
  supportPortalDetail: "Портал поддержки",
  agents: "Агенты",
  agentDetail: "Карточка агента",
  aiKnowledge: "Знания",
  aiKnowledgeCreate: "Создание знания",
  aiKnowledgeDetail: "Знание",
  aiUsage: "Использование AI",
  integrations: "Интеграции",
};

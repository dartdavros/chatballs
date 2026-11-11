// Восемь шагов «Начала работы»: от ключа модели до первого диалога с клиентом.
//
// Таблица описательная — она не знает ни про состояние визарда, ни про сеть.
// Порядок шагов равен порядку, в котором установку разумно настраивать: без
// провайдера молчит агент, без агента некому отвечать, без точки входа некуда
// писать.
//
// Ключ шага совпадает с именем факта в ответе `/company/onboarding/`: галочку
// ставит сервер по факту настройки, а не нажатие «Далее».

import type { SettingsSectionKey } from "../settings/sections";
import type { RouteKey } from "../../types";
import { webWidgetSnippet } from "../integrations/model";
import { t } from "../../i18n";

export type OnboardingStepKey =
  | "providerConnected"
  | "agentActive"
  | "knowledgeFilled"
  | "connectionBound"
  | "widgetPublished"
  | "employeeInvited"
  | "platformConfigured"
  | "firstConversation";

export type OnboardingProgress = Record<OnboardingStepKey, boolean>;

/** Элемент интерфейса, который подсвечивает тур: `data-onboarding-target`. */
export type TourTarget =
  | "nav-agents"
  | "nav-knowledge"
  | "nav-employees"
  | "nav-ai-providers"
  | "nav-messengers"
  | "nav-widgets"
  | "settings-platform"
  | "chat-list";

export type PreviewRow = { label: string; value: string };

export type OnboardingStep = {
  key: OnboardingStepKey;
  name: string;
  time: string;
  title: string;
  lead: string;
  /** Хлебные крошки пути до раздела. */
  path: string[];
  instructions: string[];
  warning: string;
  preview: {
    label: string;
    rows: PreviewRow[];
    chip: string;
    /** «Ожидание» — жёлтый чип: результат шага виден не сразу. */
    tone: "success" | "waiting";
    code?: string;
  };
  /** Куда ведёт «Открыть раздел» и что подсвечивает «Показать где». */
  target: { route: RouteKey; section?: SettingsSectionKey; element: TourTarget; title: string; text: string };
  /** Раздел «Платформа» есть только у администратора установки. */
  instanceOnly?: boolean;
};

// Путь в словаре хранится одной строкой со стрелками: переводчику так понятнее,
// чем три отдельных ключа, а крошки получаются разбором.
function crumbs(path: string): string[] {
  return path.split("→").map((crumb) => crumb.trim()).filter(Boolean);
}

const STEPS: OnboardingStep[] = [
  {
    key: "providerConnected",
    name: t("onboarding.s1.name"),
    time: t("onboarding.s1.time"),
    title: t("onboarding.s1.title"),
    lead: t("onboarding.s1.lead"),
    path: crumbs(t("onboarding.s1.path")),
    instructions: [t("onboarding.s1.do_1"), t("onboarding.s1.do_2"), t("onboarding.s1.do_3"), t("onboarding.s1.do_4")],
    warning: t("onboarding.s1.warning"),
    preview: {
      label: t("onboarding.s1.preview"),
      rows: [
        { label: t("onboarding.s1.row1_label"), value: t("onboarding.s1.row1_value") },
        { label: t("onboarding.s1.row2_label"), value: t("onboarding.s1.row2_value") },
        { label: t("onboarding.s1.row3_label"), value: t("onboarding.s1.row3_value") },
      ],
      chip: t("onboarding.s1.chip"),
      tone: "success",
    },
    target: { route: "aiProviders", element: "nav-ai-providers", title: t("onboarding.s1.tour_title"), text: t("onboarding.s1.tour_text") },
  },
  {
    key: "agentActive",
    name: t("onboarding.s2.name"),
    time: t("onboarding.s2.time"),
    title: t("onboarding.s2.title"),
    lead: t("onboarding.s2.lead"),
    path: crumbs(t("onboarding.s2.path")),
    instructions: [t("onboarding.s2.do_1"), t("onboarding.s2.do_2"), t("onboarding.s2.do_3"), t("onboarding.s2.do_4"), t("onboarding.s2.do_5")],
    warning: t("onboarding.s2.warning"),
    preview: {
      label: t("onboarding.s2.preview"),
      rows: [
        { label: t("onboarding.s2.row1_label"), value: t("onboarding.s2.row1_value") },
        { label: t("onboarding.s2.row2_label"), value: t("onboarding.s2.row2_value") },
        { label: t("onboarding.s2.row3_label"), value: t("onboarding.s2.row3_value") },
      ],
      chip: t("onboarding.s2.chip"),
      tone: "success",
    },
    target: { route: "agents", element: "nav-agents", title: t("onboarding.s2.tour_title"), text: t("onboarding.s2.tour_text") },
  },
  {
    key: "knowledgeFilled",
    name: t("onboarding.s3.name"),
    time: t("onboarding.s3.time"),
    title: t("onboarding.s3.title"),
    lead: t("onboarding.s3.lead"),
    path: crumbs(t("onboarding.s3.path")),
    instructions: [t("onboarding.s3.do_1"), t("onboarding.s3.do_2"), t("onboarding.s3.do_3"), t("onboarding.s3.do_4")],
    warning: t("onboarding.s3.warning"),
    preview: {
      label: t("onboarding.s3.preview"),
      rows: [
        { label: t("onboarding.s3.row1_label"), value: t("onboarding.s3.row1_value") },
        { label: t("onboarding.s3.row2_label"), value: t("onboarding.s3.row2_value") },
        { label: t("onboarding.s3.row3_label"), value: t("onboarding.s3.row3_value") },
      ],
      chip: t("onboarding.s3.chip"),
      tone: "success",
    },
    target: { route: "knowledge", element: "nav-knowledge", title: t("onboarding.s3.tour_title"), text: t("onboarding.s3.tour_text") },
  },
  {
    key: "connectionBound",
    name: t("onboarding.s4.name"),
    time: t("onboarding.s4.time"),
    title: t("onboarding.s4.title"),
    lead: t("onboarding.s4.lead"),
    path: crumbs(t("onboarding.s4.path")),
    instructions: [t("onboarding.s4.do_1"), t("onboarding.s4.do_2"), t("onboarding.s4.do_3"), t("onboarding.s4.do_4"), t("onboarding.s4.do_5")],
    warning: t("onboarding.s4.warning"),
    preview: {
      label: t("onboarding.s4.preview"),
      rows: [
        { label: t("onboarding.s4.row1_label"), value: t("onboarding.s4.row1_value") },
        { label: t("onboarding.s4.row2_label"), value: t("onboarding.s4.row2_value") },
        { label: t("onboarding.s4.row3_label"), value: t("onboarding.s4.row3_value") },
      ],
      chip: t("onboarding.s4.chip"),
      tone: "success",
    },
    target: { route: "messengers", element: "nav-messengers", title: t("onboarding.s4.tour_title"), text: t("onboarding.s4.tour_text") },
  },
  {
    key: "widgetPublished",
    name: t("onboarding.s5.name"),
    time: t("onboarding.s5.time"),
    title: t("onboarding.s5.title"),
    lead: t("onboarding.s5.lead"),
    path: crumbs(t("onboarding.s5.path")),
    instructions: [t("onboarding.s5.do_1"), t("onboarding.s5.do_2"), t("onboarding.s5.do_3"), t("onboarding.s5.do_4")],
    warning: t("onboarding.s5.warning"),
    preview: {
      label: t("onboarding.s5.preview"),
      rows: [{ label: t("onboarding.s5.row1_label"), value: t("onboarding.s5.row1_value") }],
      chip: t("onboarding.s5.chip"),
      tone: "success",
      // Тег ровно тот, что выдаёт раздел виджета, — с образцовым ключом.
      code: webWidgetSnippet("wgt_9f2c41d8"),
    },
    target: { route: "widgets", element: "nav-widgets", title: t("onboarding.s5.tour_title"), text: t("onboarding.s5.tour_text") },
  },
  {
    key: "employeeInvited",
    name: t("onboarding.s6.name"),
    time: t("onboarding.s6.time"),
    title: t("onboarding.s6.title"),
    lead: t("onboarding.s6.lead"),
    path: crumbs(t("onboarding.s6.path")),
    instructions: [t("onboarding.s6.do_1"), t("onboarding.s6.do_2"), t("onboarding.s6.do_3"), t("onboarding.s6.do_4")],
    warning: t("onboarding.s6.warning"),
    preview: {
      label: t("onboarding.s6.preview"),
      rows: [
        { label: t("onboarding.s6.row1_label"), value: t("onboarding.s6.row1_value") },
        { label: t("onboarding.s6.row2_label"), value: t("onboarding.s6.row2_value") },
        { label: t("onboarding.s6.row3_label"), value: t("onboarding.s6.row3_value") },
      ],
      chip: t("onboarding.s6.chip"),
      tone: "waiting",
    },
    target: { route: "employees", element: "nav-employees", title: t("onboarding.s6.tour_title"), text: t("onboarding.s6.tour_text") },
  },
  {
    key: "platformConfigured",
    name: t("onboarding.s7.name"),
    time: t("onboarding.s7.time"),
    title: t("onboarding.s7.title"),
    lead: t("onboarding.s7.lead"),
    path: crumbs(t("onboarding.s7.path")),
    instructions: [t("onboarding.s7.do_1"), t("onboarding.s7.do_2"), t("onboarding.s7.do_3"), t("onboarding.s7.do_4")],
    warning: t("onboarding.s7.warning"),
    preview: {
      label: t("onboarding.s7.preview"),
      rows: [
        { label: t("onboarding.s7.row1_label"), value: t("onboarding.s7.row1_value") },
        { label: t("onboarding.s7.row2_label"), value: t("onboarding.s7.row2_value") },
        { label: t("onboarding.s7.row3_label"), value: t("onboarding.s7.row3_value") },
      ],
      chip: t("onboarding.s7.chip"),
      tone: "success",
    },
    target: { route: "settings", section: "platform", element: "settings-platform", title: t("onboarding.s7.tour_title"), text: t("onboarding.s7.tour_text") },
    instanceOnly: true,
  },
  {
    key: "firstConversation",
    name: t("onboarding.s8.name"),
    time: t("onboarding.s8.time"),
    title: t("onboarding.s8.title"),
    lead: t("onboarding.s8.lead"),
    path: crumbs(t("onboarding.s8.path")),
    instructions: [t("onboarding.s8.do_1"), t("onboarding.s8.do_2"), t("onboarding.s8.do_3"), t("onboarding.s8.do_4")],
    warning: t("onboarding.s8.warning"),
    preview: {
      label: t("onboarding.s8.preview"),
      rows: [
        { label: t("onboarding.s8.row1_label"), value: t("onboarding.s8.row1_value") },
        { label: t("onboarding.s8.row2_label"), value: t("onboarding.s8.row2_value") },
        { label: t("onboarding.s8.row3_label"), value: t("onboarding.s8.row3_value") },
      ],
      chip: t("onboarding.s8.chip"),
      tone: "success",
    },
    target: { route: "chat", element: "chat-list", title: t("onboarding.s8.tour_title"), text: t("onboarding.s8.tour_text") },
  },
];

/** Шаги, доступные этому человеку: «Домен и почта» — только администратору
 *  установки, у остальных шагов семь, и счётчик считает от семи. */
export function visibleOnboardingSteps(isInstanceAdmin: boolean): OnboardingStep[] {
  return STEPS.filter((step) => !step.instanceOnly || isInstanceAdmin);
}

export const EMPTY_PROGRESS: OnboardingProgress = {
  providerConnected: false,
  agentActive: false,
  knowledgeFilled: false,
  connectionBound: false,
  widgetPublished: false,
  employeeInvited: false,
  platformConfigured: false,
  firstConversation: false,
};

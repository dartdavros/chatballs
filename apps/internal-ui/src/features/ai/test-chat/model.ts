export type TestChannel = "MAX" | "TG" | "WEB";

export const testChannels: Array<{ key: TestChannel; label: string; dot: string }> = [
  { key: "MAX", label: "MAX", dot: "#6b5be0" },
  { key: "TG", label: "TG", dot: "#2f8fd0" },
  { key: "WEB", label: "Web", dot: "#0f9b8e" },
];

export const testScenarios = [
  { id: "box", title: "Покупка коробки", desc: "Клиент хочет купить FirePage под визитку." },
  { id: "support", title: "Вопрос про поддержку", desc: "Уточняет условия годовой поддержки." },
  { id: "handoff", title: "Запрос человека", desc: "Просит соединить с менеджером." },
];

export const diagnosticChunks = [
  { source: "Что входит в коробку FirePage", score: "0.91", text: "Коробка FirePage — готовый нишевой сайт под ключ, единоразовая оплата ₽4 900." },
  { source: "Условия годовой поддержки", score: "0.84", text: "Годовая поддержка — 30% от цены коробки, ₽1 470 в год, продление по желанию." },
];

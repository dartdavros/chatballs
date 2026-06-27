export type ClientDetailTab = "overview" | "dialogs" | "orders" | "ids" | "consent" | "audit";

export const clientDetailTabs: Array<{ key: ClientDetailTab; label: string }> = [
  { key: "overview", label: "Обзор" },
  { key: "dialogs", label: "Диалоги" },
  { key: "orders", label: "Заказы" },
  { key: "ids", label: "Идентификаторы каналов" },
  { key: "consent", label: "Consent" },
  { key: "audit", label: "Аудит" },
];

export const salesClientDetail = {
  name: "Елена Кузнецова",
  initials: "ЕК",
  cid: "CUS-4702",
  email: "e.kuznetsova@corp.ru",
  phone: "+7 ··· ·· 88",
  avatarBg: "#9254de",
  channels: [
    { label: "MAX", color: "#6b5be0", bg: "#f2f0ff" },
    { label: "Web", color: "#0f9b8e", bg: "#e8f7f4" },
  ],
  summary: [
    { label: "Заказы", value: "3" },
    { label: "Сумма покупок", value: "₽9 800", accent: true },
    { label: "Диалоги", value: "4" },
    { label: "Первый контакт", value: "28 мая 2026", compact: true },
  ],
  note: "Ортодонт-центр, ведёт приём. Пользуется Foxray Про (безлимит пациентов), оценивает тариф Макс. Также купила готовый сайт FirePage. Платит картой, ЛПР — сама Елена.",
  activity: [
    { title: "Создан заказ", code: "ORD-10512", suffix: "· Foxray Про (год)", time: "сегодня 11:05", color: "#1677ff" },
    { title: "Оплата ₽4 900 ·", code: "ORD-10455", time: "02 июня 18:22", color: "#52c41a" },
    { title: "Диалог закрыт · продажа Foxray Про", time: "02 июня 14:00", color: "#722ed1" },
    { title: "Первый контакт · канал MAX", time: "28 мая 2026", color: "#bfbfbf" },
  ],
  dialogs: [
    { title: "Настройка доступа · Foxray", meta: "Web Chat · ведёт Иван Петров", status: "Оператор", time: "18 мин назад", active: true },
    { title: "Покупка Foxray Про", meta: "MAX · закрыт · продажа", status: "Закрыт", time: "02 июня" },
    { title: "Консультация по тарифам", meta: "MAX · закрыт", status: "Закрыт", time: "28 мая" },
    { title: "Первичный вопрос о продукте", meta: "MAX · закрыт", status: "Закрыт", time: "28 мая" },
  ],
  orders: [
    { id: "ORD-10512", date: "сегодня 11:05", product: "Foxray · Про (год)", amount: "₽47 040", payment: "Ожидает", fulfillment: "—" },
    { id: "ORD-10455", date: "02 июня", product: "Foxray · Про", amount: "₽4 900", payment: "Оплачен", fulfillment: "Доступ активен" },
    { id: "ORD-10390", date: "28 мая", product: "FirePage · Beauty Tiffany", amount: "₽4 900", payment: "Оплачен", fulfillment: "Лицензия выдана" },
  ],
  identities: [
    { name: "MAX", value: "@elena.kuz", status: "основной · подтверждён", color: "#6b5be0", bg: "#f2f0ff", ok: true },
    { name: "Web Chat", value: "session 9f2a···", status: "активна", color: "#0f9b8e", bg: "#e8f7f4", ok: true },
    { name: "Email", value: "e.kuznetsova@corp.ru", status: "подтверждён", icon: "mail" as const, ok: true },
    { name: "Телефон", value: "+7 ··· ·· 88 · скрыт", status: "не подтверждён", icon: "phone" as const },
  ],
  consent: [
    { title: "Согласие на обработку данных · получено", meta: "Канал MAX · подтверждено пользователем", time: "04 июня 2026, 14:20", ok: true },
    { title: "Согласие на маркетинговые сообщения · получено", meta: "Канал MAX", time: "04 июня 2026, 14:20", ok: true },
    { title: "Первичный контакт · согласие ещё не получено", meta: "Канал MAX · обработка по законному интересу", time: "28 мая 2026" },
  ],
  audit: [
    { time: "сегодня 11:05", action: "Создан заказ", object: "ORD-10512", actor: "AI-агент", result: "успешно", ai: true },
    { time: "02 июня 18:22", action: "Объединение контактов", object: "CUS-4702 ← CUS-4810", actor: "Иван Петров", result: "успешно" },
    { time: "02 июня 14:00", action: "Изменены контактные данные", object: "email", actor: "Иван Петров", result: "успешно" },
    { time: "28 мая 2026", action: "Контакт создан", object: "CUS-4702", actor: "система", result: "успешно", muted: true },
  ],
};

import type { SalesFulfillment, SalesOrder, SalesOrdersTab, SalesPayment, SalesRefund, SalesSubscription, StatusTone } from "./types";

const statusTone = {
  green: { color: "#389e0d", bg: "#f6ffed" },
  amber: { color: "#d48806", bg: "#fffbe6" },
  red: { color: "#cf1322", bg: "#fff2f0" },
  blue: { color: "#0958d9", bg: "#e6f4ff" },
  gray: { color: "#8c8c8c", bg: "#f5f5f5" },
  purple: { color: "#722ed1", bg: "#f9f0ff" },
} satisfies Record<StatusTone, { color: string; bg: string }>;

const sourceColor = {
  MAX: "#6b5be0",
  Telegram: "#2f8fd0",
  Web: "#0f9b8e",
} satisfies Record<string, string>;

export const salesOrderTabs: Array<{ key: SalesOrdersTab; label: string; count: number }> = [
  { key: "orders", label: "Заказы", count: 6 },
  { key: "subs", label: "Подписки", count: 4 },
  { key: "pays", label: "Платежи", count: 5 },
  { key: "refunds", label: "Возвраты", count: 3 },
  { key: "exec", label: "Исполнение", count: 4 },
];

function badge(value: `${StatusTone}:${string}`) {
  const [tone, label] = value.split(":") as [StatusTone, string];
  return { ...statusTone[tone], label };
}

function search(...parts: string[]) {
  return parts.join(" ").toLowerCase();
}

export const salesOrders: SalesOrder[] = [
  { id: "ORD-10519", date: "сегодня 14:02", client: "Татьяна Лебедева", offer: "FirePage · Business", amount: "₽2 490", pay: badge("green:Оплачен"), fulfillment: badge("green:Исполнен"), source: { label: "MAX", color: sourceColor.MAX }, seller: "AI-агент", sellerAI: true, search: search("ORD-10519", "Татьяна Лебедева") },
  { id: "ORD-10518", date: "сегодня 13:40", client: "Анна Морозова", offer: "Foxray · Pro", amount: "₽990", pay: badge("green:Оплачен"), fulfillment: badge("green:Исполнен"), source: { label: "Telegram", color: sourceColor.Telegram }, seller: "Анна Котова", search: search("ORD-10518", "Анна Морозова") },
  { id: "ORD-10516", date: "сегодня 12:18", client: "Павел Новиков", offer: "FirePage · Business", amount: "₽2 490", pay: badge("green:Оплачен"), fulfillment: badge("blue:В процессе"), source: { label: "MAX", color: sourceColor.MAX }, seller: "AI-агент", sellerAI: true, search: search("ORD-10516", "Павел Новиков") },
  { id: "ORD-10512", date: "сегодня 11:05", client: "Елена Кузнецова", offer: "Foxray · Team", amount: "₽4 980", pay: badge("amber:Ожидает"), fulfillment: badge("gray:—"), source: { label: "Web", color: sourceColor.Web }, seller: "Иван Петров", search: search("ORD-10512", "Елена Кузнецова") },
  { id: "ORD-10508", date: "вчера 18:22", client: "Игорь Соколов", offer: "Foxray · Pro", amount: "₽990", pay: badge("gray:Возврат"), fulfillment: badge("green:Исполнен"), source: { label: "MAX", color: sourceColor.MAX }, seller: "AI-агент", sellerAI: true, search: search("ORD-10508", "Игорь Соколов") },
  { id: "ORD-10482", date: "вчера 16:50", client: "Сергей Волков", offer: "FirePage · Business", amount: "₽2 490", pay: badge("red:Не оплачен"), fulfillment: badge("gray:—"), source: { label: "Telegram", color: sourceColor.Telegram }, seller: "AI-агент", sellerAI: true, search: search("ORD-10482", "Сергей Волков") },
];

export const salesSubscriptions: SalesSubscription[] = [
  { id: "SUB-2041", client: "Татьяна Лебедева", offer: "FirePage Business · мес", status: badge("green:Активна"), period: "16 июн — 16 июл", next: "16 июл 2026", entitlement: "10 мест", search: search("SUB-2041", "Татьяна Лебедева") },
  { id: "SUB-2038", client: "Анна Морозова", offer: "Foxray Pro · мес", status: badge("green:Активна"), period: "02 июн — 02 июл", next: "02 июл 2026", entitlement: "1 место", search: search("SUB-2038", "Анна Морозова") },
  { id: "SUB-2025", client: "Игорь Соколов", offer: "Foxray Pro · мес", status: badge("gray:Отменена"), period: "—", next: "—", entitlement: "—", search: search("SUB-2025", "Игорь Соколов") },
  { id: "SUB-2011", client: "Елена Кузнецова", offer: "Foxray Team · год", status: badge("amber:Приостановлена"), period: "10 мар — 10 мар 27", next: "пауза", entitlement: "5 мест", search: search("SUB-2011", "Елена Кузнецова") },
];

export const salesPayments: SalesPayment[] = [
  { id: "PAY-88231", order: "ORD-10519", provider: "Точка", amount: "₽2 490", status: badge("green:Успешно"), method: "Карта ···4242", date: "сегодня 14:02", reconcile: { color: statusTone.green.color, label: "Сверено" }, search: search("PAY-88231", "ORD-10519") },
  { id: "PAY-88230", order: "ORD-10518", provider: "Точка", amount: "₽990", status: badge("green:Успешно"), method: "СБП", date: "сегодня 13:40", reconcile: { color: statusTone.green.color, label: "Сверено" }, search: search("PAY-88230", "ORD-10518") },
  { id: "PAY-88224", order: "ORD-10512", provider: "Точка", amount: "₽4 980", status: badge("amber:Ожидает"), method: "Карта", date: "сегодня 11:05", reconcile: { color: statusTone.amber.color, label: "Ожидает сверки" }, search: search("PAY-88224", "ORD-10512") },
  { id: "PAY-88210", order: "ORD-10508", provider: "Точка", amount: "₽990", status: badge("gray:Возврат"), method: "Карта ···1188", date: "вчера 18:25", reconcile: { color: statusTone.green.color, label: "Сверено" }, search: search("PAY-88210", "ORD-10508") },
  { id: "PAY-88198", order: "ORD-10482", provider: "Точка", amount: "₽2 490", status: badge("red:Отклонён"), method: "Карта ···7701", date: "вчера 16:51", reconcile: { color: statusTone.gray.color, label: "—" }, search: search("PAY-88198", "ORD-10482") },
];

export const salesRefunds: SalesRefund[] = [
  { id: "REF-3120", reference: "ORD-10508 · PAY-88210", amount: "₽990", reason: "Запрос клиента", status: badge("green:Завершён"), actor: "Иван Петров", date: "сегодня 09:14", search: search("REF-3120", "ORD-10508 · PAY-88210") },
  { id: "REF-3118", reference: "ORD-10455 · PAY-87990", amount: "₽2 490", reason: "Дубль оплаты", status: badge("amber:В обработке"), actor: "OWNER", date: "вчера 20:02", search: search("REF-3118", "ORD-10455 · PAY-87990") },
  { id: "REF-3101", reference: "ORD-10390 · PAY-87740", amount: "₽4 980", reason: "Брак поставки", status: badge("red:Отклонён"), actor: "Иван Петров", date: "13 июн", search: search("REF-3101", "ORD-10390 · PAY-87740") },
];

export const salesFulfillment: SalesFulfillment[] = [
  { order: "ORD-10519", product: "FirePage", operation: "OP-55120", status: badge("green:Успешно"), attempts: "1", error: "—", updated: "сегодня 14:03", canRetry: false, search: search("ORD-10519", "OP-55120") },
  { order: "ORD-10516", product: "FirePage", operation: "OP-55117", status: badge("blue:В процессе"), attempts: "1", error: "—", updated: "сегодня 12:19", canRetry: false, search: search("ORD-10516", "OP-55117") },
  { order: "ORD-10512", product: "Foxray", operation: "OP-55110", status: badge("amber:Ожидает оплаты"), attempts: "0", error: "—", updated: "сегодня 11:05", canRetry: false, search: search("ORD-10512", "OP-55110") },
  { order: "ORD-10470", product: "Foxray", operation: "OP-55088", status: badge("red:Ошибка"), attempts: "3", error: "TIMEOUT: provider 504", updated: "вчера 15:40", canRetry: true, search: search("ORD-10470", "OP-55088") },
];

export const salesOrdersData = {
  orders: salesOrders,
  subs: salesSubscriptions,
  pays: salesPayments,
  refunds: salesRefunds,
  exec: salesFulfillment,
};

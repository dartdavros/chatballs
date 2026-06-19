import type { RouteKey } from "../../../types";

export type OrderDetailTab = "summary" | "pays" | "receipts" | "fulfillment" | "subscription" | "audit";

export type OrderDetail = typeof salesOrderDetail;

export const orderDetailTabs: Array<{ key: OrderDetailTab; label: string }> = [
  { key: "summary", label: "Состав" },
  { key: "pays", label: "Платежи" },
  { key: "receipts", label: "Чеки" },
  { key: "fulfillment", label: "Исполнение" },
  { key: "subscription", label: "Подписка" },
  { key: "audit", label: "Аудит" },
];

export const salesOrderDetail = {
  id: "ORD-10519",
  status: "Выполнен · подписка активна",
  amount: "₽2 490",
  amountPeriod: "/ мес",
  client: "Татьяна Лебедева",
  clientRoute: "salesClientDetail" as RouteKey,
  offer: "FirePage · Business",
  date: "16 июня 2026",
  source: { label: "MAX", color: "#6b5be0" },
  seller: "AI-агент",
  sellerColor: "#722ed1",
  timeline: [
    { label: "Оформление", time: "14:00", done: true },
    { label: "Заказ", time: "14:01", done: true },
    { label: "Оплата", time: "14:02", done: true },
    { label: "Чек", time: "14:02", done: true },
    { label: "Исполнение", time: "14:03", done: true },
    { label: "Доступ", time: "активен", done: true, active: true },
    { label: "Возврат", time: "нет", done: false },
  ],
  items: [
    { offer: "FirePage · Business", code: "OFR-FP-BUS · цена v4", type: "Подписка · мес", price: "₽2 490", qty: "1", total: "₽2 490" },
  ],
  documents: [
    { title: "Публичная оферта", version: "v3.1", accepted: "принято 16 июня 14:00" },
    { title: "Политика обработки персональных данных", accepted: "принято 16 июня 14:00" },
  ],
  buyer: {
    name: "Татьяна Лебедева",
    email: "t.lebedeva@agency.ru",
    company: "ООО «Агентство Лебедева» · ИНН 7701234567",
  },
  checkout: {
    title: "Канал MAX · диалог с AI-агентом",
    id: "оформление CHK-77120 →",
    created: "создан 16 июня 14:00",
  },
  payments: {
    rows: [
      { id: "PAY-88231", provider: "Точка", amount: "₽2 490", method: "Карта ···4242", status: "Успешно", reconcile: "Сверено" },
    ],
    events: [
      { name: "Платёж авторизован", id: "evt_8831a", time: "14:02:03" },
      { name: "Платёж списан", id: "evt_8831b", time: "14:02:05" },
      { name: "Платёж сверен", id: "evt_8832c", time: "02:10" },
    ],
  },
  receipt: [
    { label: "Чек", value: "RCP-44021", mono: true },
    { label: "Тип", value: "Приход" },
    { label: "Фискальный признак (ФПД)", value: "3920··· 7741", mono: true },
    { label: "Сумма", value: "₽2 490 · НДС 20%" },
    { label: "ОФД", value: "Принят · 16 июня 14:02" },
    { label: "Отправлен клиенту", value: "Почта · доставлен" },
  ],
  fulfillment: {
    id: "OP-55120 · FirePage",
    attempts: "1",
    result: "Успешно",
    updated: "16 июня 14:03",
    payload: "продукт: FirePage\nтариф: Business\nрабочие места: 10\nаккаунт: agency-lebedeva\nактивация: 16 июня 2026 14:03",
  },
  subscription: {
    id: "SUB-2041 · FirePage Business",
    period: "16 июн — 16 июл 2026",
    next: "16 июля 2026 · ₽2 490",
    entitlement: "10 рабочих мест",
  },
  audit: [
    { time: "16 июня 14:03", action: "Исполнение выполнено · OP-55120", actor: "система", actorTone: "muted", result: "успешно" },
    { time: "16 июня 14:02", action: "Чек отправлен в ОФД · RCP-44021", actor: "система", actorTone: "muted", result: "успешно" },
    { time: "16 июня 14:02", action: "Платёж получен · PAY-88231", actor: "Точка", actorTone: "default", result: "успешно" },
    { time: "16 июня 14:01", action: "Заказ создан · ORD-10519", actor: "AI-агент", actorTone: "ai", result: "успешно" },
    { time: "16 июня 14:00", action: "Оформление создано · CHK-77120", actor: "AI-агент", actorTone: "ai", result: "успешно" },
  ],
};

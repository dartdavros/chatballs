import type { RouteKey } from "../../../types";

export type OrderDetailTab = "summary" | "pays" | "receipts" | "fulfillment" | "subscription" | "audit";

export type OrderDetail = typeof salesOrderDetail;

export const orderDetailTabs: Array<{ key: OrderDetailTab; label: string }> = [
  { key: "summary", label: "Состав" },
  { key: "pays", label: "Платежи" },
  { key: "receipts", label: "Чеки" },
  { key: "fulfillment", label: "Доступ продукта" },
  { key: "subscription", label: "Подписка" },
  { key: "audit", label: "Аудит" },
];

export const salesOrderDetail = {
  id: "ORD-10519",
  status: "Активна · доступ активен",
  amount: "₽4 900",
  amountPeriod: "/ мес",
  client: "Елена Кузнецова",
  clientRoute: "salesClientDetail" as RouteKey,
  offer: "Foxray · Про",
  date: "16 июня 2026",
  source: { label: "MAX", color: "#6b5be0" },
  seller: "AI-агент",
  sellerColor: "#722ed1",
  timeline: [
    { label: "Ссылка покупки", time: "14:00", done: true },
    { label: "Заказ", time: "14:01", done: true },
    { label: "Оплата", time: "14:02", done: true },
    { label: "Чек", time: "14:02", done: true },
    { label: "Доступ", time: "активен", done: true, active: true },
    { label: "Возврат", time: "нет", done: false },
  ],
  items: [
    { offer: "Foxray · Про", code: "OFR-FX-PRO · цена v2", type: "Подписка · мес", price: "₽4 900", qty: "1", total: "₽4 900" },
  ],
  documents: [
    { title: "Публичная оферта", version: "v3.1", accepted: "принято 16 июня 14:00" },
    { title: "Политика обработки персональных данных", accepted: "принято 16 июня 14:00" },
  ],
  buyer: {
    name: "Елена Кузнецова",
    email: "e.kuznetsova@corp.ru",
    company: "ООО «Ортодонт-Центр» · ИНН 7701234567",
  },
  checkout: {
    title: "Канал MAX · диалог с AI-агентом",
    id: "ссылка покупки CHK-77120 →",
    created: "создана 16 июня 14:00",
  },
  payments: {
    rows: [
      { id: "PAY-88231", provider: "Точка", amount: "₽4 900", method: "Карта ···4242", status: "Успешно", reconcile: "Сверено" },
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
    { label: "Сумма", value: "₽4 900 · без НДС (УСН)" },
    { label: "ОФД", value: "Принят · 16 июня 14:02" },
    { label: "Отправлен клиенту", value: "Почта · доставлен" },
  ],
  fulfillment: {
    id: "OP-55110 · Foxray",
    attempts: "1",
    result: "Доступ активен",
    updated: "16 июня 14:03",
    payload: "продукт: Foxray\nтариф: Про\nдоступ: безлимит пациентов\nаккаунт: clinic-kuznetsova\nактивация: 16 июня 2026 14:03",
  },
  subscription: {
    id: "SUB-2041 · Foxray Про",
    period: "16 июн — 16 июл 2026",
    next: "16 июля 2026 · ₽4 900",
    entitlement: "Безлимит пациентов",
  },
  audit: [
    { time: "16 июня 14:03", action: "Доступ активирован · OP-55110", actor: "продукт", actorTone: "muted", result: "успешно" },
    { time: "16 июня 14:02", action: "Чек отправлен в ОФД · RCP-44021", actor: "продукт", actorTone: "muted", result: "успешно" },
    { time: "16 июня 14:02", action: "Платёж получен · PAY-88231", actor: "Точка", actorTone: "default", result: "успешно" },
    { time: "16 июня 14:01", action: "Заказ создан · ORD-10519", actor: "AI-агент", actorTone: "ai", result: "успешно" },
    { time: "16 июня 14:00", action: "Ссылка покупки создана · CHK-77120", actor: "AI-агент", actorTone: "ai", result: "успешно" },
  ],
};

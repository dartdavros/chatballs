import type { Product } from "../../../types";
import { chartPaths } from "./chart";
import type { KpiItem, SalesPeriod } from "./types";

export function salesOverviewModel(period: SalesPeriod, products: Product[]) {
  const f = period === "d7" ? 7 : period === "d30" ? 30 : 1;
  const fmt = (n: number) => `₽${Math.round(n).toLocaleString("ru-RU").replace(/\u00a0/g, " ")}`;
  const periodLabel = { today: "Сегодня", d7: "7 дней", d30: "30 дней" }[period];
  const res = {
    today: { sales: "18", rev: fmt(146200), conv: "14,2%", aiCost: fmt(1240), perSale: fmt(69) },
    d7: { sales: "126", rev: fmt(1024600), conv: "13,6%", aiCost: fmt(8600), perSale: fmt(68) },
    d30: { sales: "540", rev: fmt(4386000), conv: "13,1%", aiCost: fmt(36400), perSale: fmt(67) },
  }[period];
  const up = "#389e0d";
  const opsKpi: KpiItem[] = [
    { label: "Открытые диалоги", value: "42", sub: "в работе" },
    { label: "Активные сейчас", value: "9", sub: "за 15 минут" },
    { label: "На AI", value: "35", sub: "83% диалогов", dot: "#722ed1" },
    { label: "На операторах", value: "7", sub: "17% диалогов", dot: "#1677ff" },
    { label: "Ожидают оператора", value: "0", valueColor: up, sub: "очередь пуста", subColor: up },
  ];
  const resKpi: KpiItem[] = [
    { label: "Продажи", value: res.sales, deltaText: "+12%", deltaColor: up, sub: "к пред." },
    { label: "Чистая выручка", value: res.rev, deltaText: "+8%", deltaColor: up, sub: "к пред." },
    { label: "Конверсия", value: res.conv, deltaText: "+1,3 пп", deltaColor: up, sub: "к пред." },
    { label: "Стоимость AI", value: res.aiCost, deltaText: "+4%", deltaColor: "#8c8c8c", sub: "к пред." },
    { label: "Стоимость AI / продажа", value: res.perSale, deltaText: "−3%", deltaColor: up, sub: "дешевле", down: true },
  ];
  const series = {
    today: { vals: [6, 9, 7, 14, 11, 18, 13, 16, 21, 19], labels: ["09", "10", "11", "12", "13", "14", "15", "16", "17", "18"] },
    d7: { vals: [78, 92, 85, 140, 118, 164, 150], labels: ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"] },
    d30: { vals: [120, 135, 128, 150, 142, 168, 175, 160, 182, 176, 190, 185, 205, 198, 220], labels: ["1", "5", "10", "15", "20", "25", "30"] },
  }[period];
  const chart = chartPaths(series.vals);
  const productSource = products.length > 0 ? products : [{ id: 1, code: "firepage", name: "FirePage", status: "ACTIVE" as const, siteUrl: "", createdAt: "" }, { id: 2, code: "foxray", name: "Foxray", status: "ACTIVE" as const, siteUrl: "", createdAt: "" }];
  const productBase = [
    { code: "firepage", salesN: 12, revN: 98400, conv: "15,1%", dlg: "28" },
    { code: "foxray", salesN: 6, revN: 47800, conv: "12,8%", dlg: "14" },
  ];
  const productRows = productSource.slice(0, 2).map((product, index) => {
    const base = productBase.find((item) => item.code === product.code) ?? productBase[index] ?? productBase[0];
    return { name: product.name, status: "Активен", conv: base.conv, dlg: base.dlg, sales: String(base.salesN * f), rev: fmt(base.revN * f) };
  });
  const channels = [
    { name: "MAX", color: "#6b5be0", dlg: "18", salesN: 9, share: 50 },
    { name: "Telegram", color: "#2f8fd0", dlg: "14", salesN: 6, share: 33 },
    { name: "Web Chat", color: "#0f9b8e", dlg: "10", salesN: 3, share: 17 },
  ].map((channel) => ({ ...channel, sales: String(channel.salesN * f) }));

  return {
    periodLabel,
    res,
    opsKpi,
    resKpi,
    products: productRows,
    channels,
    aiSales: String(11 * f),
    opSales: String(7 * f),
    chartTotal: res.rev,
    xLabels: series.labels,
    ...chart,
    problems: [
      { dot: "#faad14", title: "Гость 8842 · нет ответа клиента 18 мин", meta: "FirePage · Web Chat", time: "18 мин" },
      { dot: "#1677ff", title: "Длинный диалог · 24 сообщения без продажи", meta: "Foxray · Telegram", time: "32 мин" },
      { dot: "#faad14", title: "Гость 5510 · повторное обращение", meta: "Foxray · Telegram", time: "1 ч" },
    ],
    payments: [
      { dot: "#faad14", title: "Незавершённый платёж · ORD-10482", meta: "Точка · ₽2 490 · FirePage", time: "6 мин" },
      { dot: "#1677ff", title: "Подписка: продление через 2 дня", meta: "Foxray Про · ORD-10311", time: "—" },
    ],
  };
}

export type SalesOverviewVm = ReturnType<typeof salesOverviewModel>;

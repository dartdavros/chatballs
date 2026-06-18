import { useMemo, useState } from "react";

import type { Product } from "../../types";
import { Icon } from "../../shared/icons";
import { Segmented } from "../../shared/ui";

type SalesPeriod = "today" | "d7" | "d30";

export function SalesOverviewPage({ products }: { products: Product[] }) {
  const [period, setPeriod] = useState<SalesPeriod>("today");
  const vm = useMemo(() => salesOverviewModel(period, products), [period, products]);

  return (
    <>
      <div className="sales-overview-header">
        <div>
          <h1>Обзор отдела продаж</h1>
          <p>Операционное состояние и результаты · обновлено только что</p>
        </div>
        <Segmented value={period} setValue={setPeriod} items={[["today", "Сегодня"], ["d7", "7 дней"], ["d30", "30 дней"]]} />
      </div>

      <SalesSectionTitle label="ОПЕРАЦИОННЫЕ · СЕЙЧАС" />
      <div className="sales-kpi-grid">
        {vm.opsKpi.map((item) => <SalesKpiCard item={item} key={item.label} />)}
      </div>

      <SalesSectionTitle label={`РЕЗУЛЬТАТ · ${vm.periodLabel.toUpperCase()}`} />
      <div className="sales-kpi-grid">
        {vm.resKpi.map((item) => <SalesKpiCard item={item} result key={item.label} />)}
      </div>

      <section className="sales-chart-card">
        <div className="sales-chart-head">
          <div>
            <h3>Динамика продаж</h3>
            <div>
              <strong>{vm.chartTotal}</strong>
              <span><Icon name="chevron" size={13} />+8%</span>
              <small>чистая выручка · {vm.periodLabel}</small>
            </div>
          </div>
          <em><span />Выручка</em>
        </div>
        <div className="sales-chart-body">
          <svg viewBox="0 0 1000 260" preserveAspectRatio="none">
            <defs>
              <linearGradient id="salesFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor="#1677ff" stopOpacity="0.16" />
                <stop offset="1" stopColor="#1677ff" stopOpacity="0" />
              </linearGradient>
            </defs>
            {vm.gridLines.map((y) => <line x1="10" x2="990" y1={y} y2={y} stroke="#f2f2f2" strokeWidth="1" vectorEffect="non-scaling-stroke" key={y} />)}
            <path d={vm.areaPath} fill="url(#salesFill)" />
            <path d={vm.linePath} fill="none" stroke="#1677ff" strokeWidth="2.5" vectorEffect="non-scaling-stroke" strokeLinejoin="round" strokeLinecap="round" />
            <circle cx={vm.last.x} cy={vm.last.y} r="4.5" fill="#1677ff" stroke="#ffffff" strokeWidth="2.5" vectorEffect="non-scaling-stroke" />
          </svg>
          <div className="sales-chart-labels">
            {vm.xLabels.map((label) => <span key={label}>{label}</span>)}
          </div>
        </div>
      </section>

      <div className="sales-overview-grid">
        <section className="sales-table-card">
          <div className="sales-card-head">
            <h3>Продукты</h3>
            <a href="#" onClick={(event) => event.preventDefault()}>Все продукты</a>
          </div>
          <table>
            <thead>
              <tr>
                <th>ПРОДУКТ</th>
                <th>СТАТУС</th>
                <th>ПРОДАЖИ</th>
                <th>ВЫРУЧКА</th>
                <th>КОНВ.</th>
                <th>ДИАЛОГИ</th>
              </tr>
            </thead>
            <tbody>
              {vm.products.map((product) => (
                <tr key={product.name}>
                  <td><a href="#" onClick={(event) => event.preventDefault()}>{product.name}</a></td>
                  <td><span className="sales-active-status"><i />{product.status}</span></td>
                  <td>{product.sales}</td>
                  <td>{product.rev}</td>
                  <td>{product.conv}</td>
                  <td>{product.dlg}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="sales-panel-card sales-channels-card">
          <h3>Каналы</h3>
          {vm.channels.map((channel) => (
            <div className="sales-channel-row" key={channel.name}>
              <div>
                <strong><i style={{ background: channel.color }} />{channel.name}</strong>
                <span>{channel.dlg} диал. · <b>{channel.sales}</b> продаж</span>
              </div>
              <em><i style={{ width: `${channel.share}%`, background: channel.color }} /></em>
            </div>
          ))}
        </section>

        <section className="sales-panel-card sales-actors-card">
          <h3>AI и операторы</h3>
          <SalesActor title="AI-агент" tone="ai" values={[["Диалоги", "35"], ["Продажи", vm.aiSales], ["Конверсия", "13,2%"], ["Стоимость", vm.res.aiCost]]} />
          <SalesActor title="Операторы" tone="operator" values={[["Диалоги", "7"], ["Продажи", vm.opSales], ["Конверсия", "41%"], ["Передано AI→", "4"]]} />
        </section>

        <SalesListCard title="Проблемные диалоги" icon="warning" items={vm.problems} />
        <SalesListCard title="Платежи и fulfillment" icon="box" items={vm.payments} />
      </div>
    </>
  );
}

function SalesSectionTitle({ label }: { label: string }) {
  return <div className="sales-section-title">{label}</div>;
}

type KpiItem = {
  label: string;
  value: string;
  sub: string;
  dot?: string;
  valueColor?: string;
  subColor?: string;
  deltaText?: string;
  deltaColor?: string;
  down?: boolean;
};

function SalesKpiCard({ item, result = false }: { item: KpiItem; result?: boolean }) {
  return (
    <article className="sales-kpi-card">
      <span>{item.dot && <i style={{ background: item.dot }} />}{item.label}</span>
      <strong style={{ color: item.valueColor }}>{item.value}</strong>
      {result ? (
        <small className="sales-kpi-delta" style={{ color: item.deltaColor }}>
          <span className={item.down ? "is-down" : ""}><Icon name="chevron" size={13} /></span>
          {item.deltaText}<em>{item.sub}</em>
        </small>
      ) : <small style={{ color: item.subColor }}>{item.sub}</small>}
    </article>
  );
}

function SalesActor({ title, tone, values }: { title: string; tone: "ai" | "operator"; values: Array<[string, string]> }) {
  return (
    <div className={`sales-actor ${tone}`}>
      <div className="sales-actor-title"><span><i /></span>{title}</div>
      <div className="sales-actor-grid">
        {values.map(([label, value]) => <div key={label}><span>{label}</span><strong>{value}</strong></div>)}
      </div>
    </div>
  );
}

function SalesListCard({ title, icon, items }: { title: string; icon: "warning" | "box"; items: Array<{ dot: string; title: string; meta: string; time: string }> }) {
  return (
    <section className="sales-list-card">
      <div className="sales-list-head">
        <Icon name={icon} size={17} />
        <h3>{title}</h3>
      </div>
      {items.map((item) => (
        <a href="#" onClick={(event) => event.preventDefault()} key={item.title}>
          <span style={{ background: item.dot }} />
          <strong>{item.title}<small>{item.meta}</small></strong>
          <em>{item.time}</em>
        </a>
      ))}
    </section>
  );
}

function salesOverviewModel(period: SalesPeriod, products: Product[]) {
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
      { dot: "#1677ff", title: "Подписка: продление через 2 дня", meta: "Foxray Pro · ORD-10311", time: "—" },
    ],
  };
}

function chartPaths(values: number[]) {
  const width = 1000;
  const height = 260;
  const padLeft = 10;
  const padRight = 10;
  const padTop = 18;
  const padBottom = 26;
  const innerWidth = width - padLeft - padRight;
  const innerHeight = height - padTop - padBottom;
  const max = Math.max(...values) * 1.12;
  const x = (index: number) => padLeft + innerWidth * (values.length === 1 ? 0 : index / (values.length - 1));
  const y = (value: number) => padTop + innerHeight * (1 - value / max);
  const points = values.map((value, index) => ({ x: x(index), y: y(value) }));
  const linePath = `M${points.map((point) => `${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(" L")}`;
  const areaPath = `${linePath} L${x(values.length - 1).toFixed(1)},${(padTop + innerHeight).toFixed(1)} L${padLeft.toFixed(1)},${(padTop + innerHeight).toFixed(1)} Z`;
  return {
    linePath,
    areaPath,
    last: points[points.length - 1],
    gridLines: [padTop + innerHeight * 0.25, padTop + innerHeight * 0.55, padTop + innerHeight * 0.85].map((line) => line.toFixed(1)),
  };
}

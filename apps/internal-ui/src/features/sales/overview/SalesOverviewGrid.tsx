import { Icon } from "../../../shared/icons";
import type { SalesOverviewVm } from "./model";
import type { SalesListItem } from "./types";

export function SalesOverviewGrid({ vm }: { vm: SalesOverviewVm }) {
  return (
    <div className="sales-overview-grid">
      <SalesProductsTable products={vm.products} />
      <SalesChannelsCard channels={vm.channels} />
      <SalesActorsCard vm={vm} />
      <SalesListCard title="Проблемные диалоги" icon="warning" items={vm.problems} />
      <SalesListCard title="Платежи и fulfillment" icon="box" items={vm.payments} />
    </div>
  );
}

function SalesProductsTable({ products }: { products: SalesOverviewVm["products"] }) {
  return (
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
          {products.map((product) => (
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
  );
}

function SalesChannelsCard({ channels }: { channels: SalesOverviewVm["channels"] }) {
  return (
    <section className="sales-panel-card sales-channels-card">
      <h3>Каналы</h3>
      {channels.map((channel) => (
        <div className="sales-channel-row" key={channel.name}>
          <div>
            <strong><i style={{ background: channel.color }} />{channel.name}</strong>
            <span>{channel.dlg} диал. · <b>{channel.sales}</b> продаж</span>
          </div>
          <em><i style={{ width: `${channel.share}%`, background: channel.color }} /></em>
        </div>
      ))}
    </section>
  );
}

function SalesActorsCard({ vm }: { vm: SalesOverviewVm }) {
  return (
    <section className="sales-panel-card sales-actors-card">
      <h3>AI и операторы</h3>
      <SalesActor title="AI-агент" tone="ai" values={[["Диалоги", "35"], ["Продажи", vm.aiSales], ["Конверсия", "13,2%"], ["Стоимость", vm.res.aiCost]]} />
      <SalesActor title="Операторы" tone="operator" values={[["Диалоги", "7"], ["Продажи", vm.opSales], ["Конверсия", "41%"], ["Передано AI→", "4"]]} />
    </section>
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

function SalesListCard({ title, icon, items }: { title: string; icon: "warning" | "box"; items: SalesListItem[] }) {
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

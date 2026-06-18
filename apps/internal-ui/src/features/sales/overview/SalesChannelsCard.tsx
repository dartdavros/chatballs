import type { SalesOverviewVm } from "./model";

export function SalesChannelsCard({ channels }: { channels: SalesOverviewVm["channels"] }) {
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

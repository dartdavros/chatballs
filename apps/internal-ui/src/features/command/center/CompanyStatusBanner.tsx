import type { CommandVm } from "./model";

export function CompanyStatusBanner({ vm }: { vm: CommandVm }) {
  return (
    <section className="company-status-banner" style={{ borderLeftColor: vm.st.dot }}>
      <div className="company-status-dot" style={{ background: vm.st.bg }}><span style={{ background: vm.st.dot }} /></div>
      <div className="company-status-text">
        <strong>Компания: {vm.st.label}</strong>
        <p>{vm.compSummary}</p>
      </div>
      <div className="company-status-metrics">
        <SmallMetric label="Отделы" value={vm.banner.departments} />
        <SmallMetric label="Открытые диалоги" value={vm.banner.open} />
        <SmallMetric label={`Выручка · ${vm.periodLabel}`} value={vm.banner.revenue} success />
      </div>
    </section>
  );
}

function SmallMetric({ label, value, success = false }: { label: string; value: string; success?: boolean }) {
  return <div><span>{label}</span><strong className={success ? "success" : ""}>{value}</strong></div>;
}

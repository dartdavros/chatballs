import type { salesClientDetail } from "./model";

type Consent = typeof salesClientDetail.consent[number];

export function SalesClientConsentTab({ consent }: { consent: Consent[] }) {
  return (
    <section className="sales-client-section-card sales-client-consent-card">
      <h3>История согласий</h3>
      <div className="sales-client-timeline consent">
        {consent.map((item, index) => (
          <div className="sales-client-timeline-row" key={item.title}>
            <div className="sales-client-timeline-mark"><span style={{ background: item.ok ? "#52c41a" : "#bfbfbf" }} />{index < consent.length - 1 && <i />}</div>
            <div className="sales-client-timeline-text">
              <div>{item.title}</div>
              <p>{item.meta}</p>
              <time>{item.time}</time>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

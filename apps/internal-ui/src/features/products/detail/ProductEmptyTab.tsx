export function ProductEmptyTab({ title, subtitle }: { title: string; subtitle?: string }) {
  return <section className="product-detail-card product-empty-tab"><h3>{title}</h3>{subtitle && <small>{subtitle}</small>}<p>—</p></section>;
}

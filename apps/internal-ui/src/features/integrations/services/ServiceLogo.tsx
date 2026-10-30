import type { ServiceAdapter } from "./types";

/** Логотип адаптера: светлый и тёмный вариант, нужный выбирает тема через CSS. */
export function ServiceLogo({ adapter, height }: { adapter: ServiceAdapter; height: number }) {
  if (!adapter.logo.light) return null;
  return (
    <span className="service-logo" style={{ height }}>
      <img className="is-light" src={adapter.logo.light} alt={adapter.title} style={{ height }} />
      <img className="is-dark" src={adapter.logo.dark || adapter.logo.light} alt={adapter.title} style={{ height }} />
    </span>
  );
}

import { useState } from "react";

import { HelpMessageIcon } from "./HelpIcons";
import type { HelpProduct } from "./types";

export function supportHref(product: HelpProduct): string | null {
  if (!product.siteUrl || !product.supportWidgetKey) return null;
  try {
    const url = new URL(product.siteUrl);
    url.searchParams.set("chatbollsSupportWidget", product.supportWidgetKey);
    return url.toString();
  } catch {
    return null;
  }
}

export function SupportLauncher({ products }: { products: HelpProduct[] }) {
  const [open, setOpen] = useState(false);
  const available = products
    .map((product) => ({ product, href: supportHref(product) }))
    .filter((item): item is { product: HelpProduct; href: string } => (
      item.product.supportAvailable && Boolean(item.href)
    ));
  if (!available.length) return null;

  return (
    <div className={`help-support-launcher ${open ? "is-open" : ""}`}>
      {open && (
        <div className="help-support-panel" role="dialog" aria-label="Связаться с поддержкой">
          <strong>Связаться с поддержкой</strong>
          <p>Откройте продукт и напишите нам из своего аккаунта.</p>
          <div className="help-support-products">
            {available.map(({ product, href }) => (
              <a href={href} key={product.code} rel="noreferrer">
                <span>{product.name}</span>
                <small>Открыть продукт</small>
              </a>
            ))}
          </div>
        </div>
      )}
      <button
        aria-expanded={open}
        aria-label={open ? "Закрыть меню поддержки" : "Связаться с поддержкой"}
        className="help-support-button"
        type="button"
        onClick={() => setOpen((current) => !current)}
      >
        <HelpMessageIcon />
      </button>
    </div>
  );
}

import { productAccent } from "../../shared/utils";

/** Продукт канала точкой-акцентом; непродуктовый канал — валидное состояние. */
export function ChannelProductMark({ product }: { product: { code: string; name: string } | null }) {
  if (!product) return <span className="channel-muted">— непродуктовый</span>;
  const accent = productAccent(product.code);
  return (
    <span className="channel-product-mark">
      <i style={{ background: accent.color }} />
      {product.name}
    </span>
  );
}

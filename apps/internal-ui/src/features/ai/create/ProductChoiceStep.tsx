import { productAccent } from "../../../shared/utils";
import type { Product } from "../../../types";
import { productDescription, productMark } from "./model";
import { CreateAgentStepCard } from "./CreateAgentStepCard";

export function ProductChoiceStep({ products, selectedProductCode, productsWithAgents, onSelect }: { products: Product[]; selectedProductCode: string | null; productsWithAgents: string[]; onSelect: (productCode: string) => void }) {
  return (
    <CreateAgentStepCard number={1} title="Продукт" text="Доступны только продукты без sales-агента. У продукта может быть не более одного агента.">
      <div className="ai-create-product-list">
        {products.map((product) => {
          const selected = selectedProductCode === product.code;
          const accent = productAccent(product.code);
          return (
            <button className={selected ? "is-selected" : ""} type="button" onClick={() => onSelect(product.code)} key={product.code}>
              <span className="ai-create-product-mark" style={{ background: accent.bg, color: accent.color }}>{productMark(product)}</span>
              <span><strong>{product.name}</strong><small>{productDescription(product)}</small></span>
              <i />
            </button>
          );
        })}
      </div>
      {productsWithAgents.length > 0 && (
        <div className="ai-create-note">
          У продуктов <b>{productsWithAgents.join(", ")}</b> агент уже есть — для них доступен переход в существующую карточку, а не создание второго.
        </div>
      )}
    </CreateAgentStepCard>
  );
}

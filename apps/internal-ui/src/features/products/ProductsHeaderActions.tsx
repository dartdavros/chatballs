import { Icon } from "../../shared/icons";
import { Segmented } from "../../shared/ui";
import type { ProductPeriod } from "./types";

export function ProductsHeaderActions({ period, setPeriod }: { period: ProductPeriod; setPeriod: (period: ProductPeriod) => void }) {
  return (
    <>
      <Segmented value={period} setValue={setPeriod} items={[["today", "Сегодня"], ["d7", "7 дней"], ["d30", "30 дней"]]} />
      <button className="primary-button" type="button"><Icon name="plus" size={16} />Создать продукт</button>
    </>
  );
}

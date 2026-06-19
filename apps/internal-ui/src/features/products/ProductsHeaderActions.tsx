import { Segmented } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
import type { ProductPeriod } from "./types";

export function ProductsHeaderActions({ period, setPeriod }: { period: ProductPeriod; setPeriod: (period: ProductPeriod) => void }) {
  return (
    <>
      <Segmented value={period} setValue={setPeriod} items={[["today", "Сегодня"], ["d7", "7 дней"], ["d30", "30 дней"]]} />
      <Button icon="plus" iconSize={16} type="button" variant="primary">Создать продукт</Button>
    </>
  );
}

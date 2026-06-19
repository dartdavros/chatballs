import { Segmented } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
import type { ProductPeriod } from "./types";

export function ProductsHeaderActions({ period, setPeriod, onCreate }: { period: ProductPeriod; setPeriod: (period: ProductPeriod) => void; onCreate: () => void }) {
  return (
    <>
      <Segmented value={period} setValue={setPeriod} items={[["today", "Сегодня"], ["d7", "7 дней"], ["d30", "30 дней"]]} />
      <Button icon="plus" iconSize={16} type="button" variant="primary" onClick={onCreate}>Создать продукт</Button>
    </>
  );
}

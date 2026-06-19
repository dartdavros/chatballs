import { Segmented } from "../../../shared/ui";
import { Button } from "../../../shared/ui-controls";
import type { CommandPeriod } from "./types";

export function CommandHeader({ period, setPeriod }: { period: CommandPeriod; setPeriod: (period: CommandPeriod) => void }) {
  return (
    <div className="command-page-header">
      <div>
        <h1>Командный центр</h1>
        <p>Состояние компании одним взглядом · обновлено только что</p>
      </div>
      <div className="command-header-actions">
        <Segmented value={period} setValue={setPeriod} items={[["today", "Сегодня"], ["d7", "7 дней"], ["d30", "30 дней"]]} />
        <Button className="refresh-button" icon="refresh" variant="secondary">Обновить</Button>
      </div>
    </div>
  );
}

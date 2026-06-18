import { useState } from "react";

import type { AppData, RouteKey } from "../../../types";
import { CommandHeader } from "./CommandHeader";
import { CommandRail } from "./CommandRail";
import { CompanyStatusBanner } from "./CompanyStatusBanner";
import { SalesDepartmentCard } from "./SalesDepartmentCard";
import { commandCenterModel } from "./model";
import type { CommandPeriod } from "./types";

export function CommandCenter({ data: _data, setRoute }: { data: AppData; setRoute: (route: RouteKey) => void }) {
  const [period, setPeriod] = useState<CommandPeriod>("today");
  const vm = commandCenterModel(period);
  return (
    <>
      <CommandHeader period={period} setPeriod={setPeriod} />
      <CompanyStatusBanner vm={vm} />
      <div className="command-two-column">
        <SalesDepartmentCard setRoute={setRoute} vm={vm} />
        <CommandRail vm={vm} />
      </div>
      <div className="command-updated">Обновлено: сегодня, 14:32 · детерминированная сводка</div>
    </>
  );
}

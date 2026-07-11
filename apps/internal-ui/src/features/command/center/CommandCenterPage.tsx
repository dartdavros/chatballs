import { useEffect, useState } from "react";

import type { AppData, RouteKey } from "../../../types";
import { EmptyState, LoadingState } from "../../../shared/ui";
import { CommandHeader } from "./CommandHeader";
import { CommandRail } from "./CommandRail";
import { CompanyStatusBanner } from "./CompanyStatusBanner";
import { DepartmentsColumn } from "./SalesDepartmentCard";
import { commandCenterModel, fetchCommandOverview, type ApiCommandOverview } from "./model";
import type { CommandPeriod } from "./types";

export function CommandCenter({ data: _data, setRoute }: { data: AppData; setRoute: (route: RouteKey) => void }) {
  const [period, setPeriod] = useState<CommandPeriod>("today");
  const [overview, setOverview] = useState<ApiCommandOverview | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    setError(false);
    fetchCommandOverview(period)
      .then((data) => { if (active) setOverview(data); })
      .catch(() => { if (active) setError(true); });
    return () => { active = false; };
  }, [period]);

  if (error) {
    return (
      <>
        <CommandHeader period={period} setPeriod={setPeriod} />
        <EmptyState title="Не удалось загрузить сводку" />
      </>
    );
  }
  if (overview === null) {
    return (
      <>
        <CommandHeader period={period} setPeriod={setPeriod} />
        <LoadingState />
      </>
    );
  }

  const vm = commandCenterModel(overview);
  return (
    <>
      <CommandHeader period={period} setPeriod={setPeriod} />
      <CompanyStatusBanner vm={vm} />
      <div className="command-two-column">
        <DepartmentsColumn setRoute={setRoute} vm={vm} />
        <CommandRail vm={vm} />
      </div>
      <div className="command-updated">Обновлено: {vm.generatedAt}</div>
    </>
  );
}

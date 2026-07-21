import { useEffect, useState } from "react";

import { PageHeader } from "../../shared/ui";
import type { AppData, RouteKey } from "../../types";
import { listChannels } from "../channels/api";
import type { Channel } from "../channels/types";
import { commandCenterModel, fetchCommandOverview, type ApiCommandOverview } from "../command/CommandCenter";
import { DepartmentCard, type DepartmentCardVm } from "./DepartmentCard";
import { departmentCopy } from "./model";
import { formatRubMinor, useDepartmentStats, type SalesDepartmentStats } from "./useDepartmentStats";

export function DepartmentsPage({ data, setRoute, openChannel }: { data: AppData; setRoute: (route: RouteKey) => void; openChannel: (channelId: number) => void }) {
  // Без channels.view список недоступен — срез каналов сообщает об этом явно,
  // а не притворяется, что каналов нет.
  const [channels, setChannels] = useState<Channel[]>([]);
  const [channelsFailed, setChannelsFailed] = useState(false);
  useEffect(() => {
    listChannels()
      .then((response) => { setChannels(response.items); setChannelsFailed(false); })
      .catch(() => setChannelsFailed(true));
  }, []);

  // Реальный статус отделов из сводки командного центра (очередь → «Требует внимания»).
  const [overview, setOverview] = useState<ApiCommandOverview | null>(null);
  useEffect(() => {
    fetchCommandOverview("today").then(setOverview).catch(() => undefined);
  }, []);
  const overviewVm = overview ? commandCenterModel(overview) : null;

  // Реальные операционные метрики отдела продаж (без выдуманных чисел).
  const stats = useDepartmentStats();

  const cards: DepartmentCardVm[] = data.departments.map((department) => {
    const copy = departmentCopy(department.code);
    return {
      id: department.id,
      code: department.code,
      name: department.name,
      memberCount: department.memberCount,
      operatorCount: department.operatorCount,
      agentCount: department.agentCount,
      status: overviewVm?.departments.find((item) => item.code === department.code)?.status ?? null,
      owner: data.employees.find((employee) => employee.department === department.code && !employee.isBlocked) ?? null,
      products: data.products.filter((product) => product.departments.some((item) => item.code === department.code)),
      channels: channels.filter((channel) => channel.departmentId === department.id),
      channelsFailed,
      stats: statsOf(department.code, stats),
      onOpen: copy.overview ? () => setRoute(copy.overview!) : null,
    };
  });

  return (
    <>
      <PageHeader title="Отделы" text={`Отделы компании · ${data.departments.length} активный(х)`} />
      <div className="departments-grid">
        {cards.map((department) => (
          <DepartmentCard department={department} openChannel={openChannel} key={department.id} />
        ))}
      </div>
    </>
  );
}

/** Прочерк вместо числа означает «метрика ещё не считается», а не ноль. */
function statsOf(code: string, stats: SalesDepartmentStats | null): [string, string, string] {
  if (code !== "sales" || !stats) return ["—", "—", "—"];
  return [String(stats.openDialogs), String(stats.sales), formatRubMinor(stats.revenueMinor)];
}

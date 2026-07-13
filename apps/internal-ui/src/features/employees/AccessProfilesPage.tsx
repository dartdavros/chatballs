import { useEffect, useState } from "react";

import { Icon } from "../../shared/icons";
import { LoadingState, PageHeader } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
import type { RouteKey } from "../../types";
import { AccessProfileEditor } from "./AccessProfileEditor";
import { AccessProfileList } from "./AccessProfileList";
import { useAccessCatalog } from "./access-api";

export function AccessProfilesPage({ setRoute }: { setRoute: (route: RouteKey) => void }) {
  const catalog = useAccessCatalog();
  const [selectedId, setSelectedId] = useState<number | null>(null);

  useEffect(() => {
    if (selectedId !== null || !catalog.profiles.length) return;
    setSelectedId(catalog.profiles[0].id);
  }, [catalog.profiles, selectedId]);

  const selected = catalog.profiles.find((profile) => profile.id === selectedId) ?? null;

  return (
    <div className="access-profiles-page">
      <button className="employee-back-link" type="button" onClick={() => setRoute("employees")}><Icon name="arrow" size={15} />Сотрудники</button>
      {/* Baseline does not define the state opened by this action; keep the approved control without inventing a form. */}
      <PageHeader title="Профили доступа" text="Именованные наборы capability организации · назначаются сотрудникам со scope" action={<Button icon="plus" iconSize={16} type="button" variant="primary">Новый профиль</Button>} />
      {catalog.loading ? <LoadingState /> : catalog.error ? <div className="access-profile-error">{catalog.error}</div> : <div className="access-profiles-layout"><AccessProfileList profiles={catalog.profiles} selectedId={selectedId} select={setSelectedId} /><AccessProfileEditor capabilities={catalog.capabilities} profile={selected} reload={catalog.reload} /></div>}
    </div>
  );
}

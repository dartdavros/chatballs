import { useState } from "react";

import { t } from "../../../../i18n";
import { EmptyState, LoadingState } from "../../../../shared/ui";
import { ServiceConnectModal } from "../connect/ServiceConnectModal";
import { DeleteServiceDialog } from "./DeleteServiceDialog";
import { ServiceCardBanners } from "./ServiceCardBanners";
import { ServiceCardHeader } from "./ServiceCardHeader";
import { ServiceConnectionBlock } from "./ServiceConnectionBlock";
import { ServicePresetsBlock } from "./ServicePresetsBlock";
import { ServiceExchangeBlock } from "./ServiceExchangeBlock";
import { useServiceCard } from "./useServiceCard";
import "../services.css";

/** Карточка подключения сервиса (кадры «Карточка · …» Сервисы.dc.html). */
export function ServiceCardPage({ connectionId, onBack, onOpenScenario }: { connectionId: number; onBack: () => void; onOpenScenario: (id: string) => void }) {
  const card = useServiceCard(connectionId);
  const [replacing, setReplacing] = useState(false);
  const [deleting, setDeleting] = useState(false);

  if (card.loading) return <LoadingState />;
  if (card.failed || !card.connection) return <EmptyState title={t("services.load_failed")} />;
  const { connection, adapter } = card;
  const service = adapter?.title ?? connection.name;

  return (
    <div className="service-card">
      <ServiceCardHeader connection={connection} adapter={adapter} onBack={onBack}
        onToggleActive={() => void card.setActive(!connection.isActive)} onDelete={() => setDeleting(true)} />
      <div className="service-card-blocks">
        {(card.failure?.message || card.failure?.error) && <div className="service-alert is-error" role="alert"><p>{card.failure.error ? `${card.failure.error.title} ${card.failure.error.text}` : card.failure.message}</p></div>}
        <ServiceCardBanners connection={connection} service={service} justConnected={card.justConnected}
          onHide={card.hideNotice} onRestore={() => setReplacing(true)} />
        {adapter && <ServicePresetsBlock adapter={adapter} connectionId={connectionId} onOpen={onOpenScenario} />}
        {adapter?.entities?.length ? <ServiceExchangeBlock connection={connection} adapter={adapter} /> : null}
        <ServiceConnectionBlock connection={connection} adapter={adapter} checking={card.checking}
          nameError={card.failure?.fields.name} onRename={(name) => void card.rename(name)}
          onCheck={() => void card.check()} onReplace={() => setReplacing(true)} />
      </div>
      {replacing && adapter && (
        <ServiceConnectModal adapter={adapter} mode={{ kind: "replace", connection }} onClose={() => setReplacing(false)}
          onDone={() => { setReplacing(false); void card.reload(); }} />
      )}
      {deleting && (
        <DeleteServiceDialog service={service} onClose={() => setDeleting(false)}
          onConfirm={async () => { await card.remove(); onBack(); }} />
      )}
    </div>
  );
}

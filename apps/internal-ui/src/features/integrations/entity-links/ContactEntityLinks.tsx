import { Dropdown } from "antd";
import { t } from "../../../i18n";
import { Icon } from "../../../shared/icons";
import { LoadingState } from "../../../shared/ui";
import { useConversationRuns } from "../runs/conversationContext";
import { useEntityLinks } from "./useEntityLinks";
import "./links.css";

export function ContactEntityLinks() {
  const state = useConversationRuns();
  const model = useEntityLinks(state?.conversationId ?? null);
  if (!state) return null;
  return <section className="run-contact-links"><h4>{t("runs.linked_records")}</h4>
    {model.error ? <p role="alert">{model.error}</p> : model.links === null ? <LoadingState variant="inline" />
      : model.links.length ? model.links.map(link => <div className="run-linked-record" key={link.id}>
        <Icon name="link" size={14} /><span>{link.url
          ? <a className="link is-strong" href={link.url} target="_blank" rel="noopener noreferrer">{link.name}</a>
          : <span>{link.name}</span>}</span><small>{link.service}</small>
        <Dropdown overlayClassName="app-dropdown" trigger={["click"]} menu={{ items: [
          { key: "open", label: <a href={link.url || undefined} target="_blank" rel="noopener noreferrer">{t("runs.open_in_service", { service: link.service })}</a>, disabled: !link.url },
          { key: "replace", label: t("runs.replace_link"), disabled: !link.searchable },
          { key: "unlink", label: t("runs.unlink"), danger: true },
        ], onClick: ({ key }) => { if (key === "replace") state.openLink(link); else if (key === "unlink") void model.unlink(link); } }}>
          <button type="button" className="row-menu-button" disabled={model.busy} aria-label={t("runs.actions")}><Icon name="more" size={14} /></button>
        </Dropdown>
      </div>) : <p>{t("runs.no_links")}</p>}
  </section>;
}

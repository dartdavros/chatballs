import { Dropdown } from "antd";
import { t } from "../i18n";
import type { RouteKey } from "../types";
import { Icon } from "./icons";
import { Button } from "./ui-controls";

export type ChannelRoute = Extract<RouteKey, "widgets" | "messengers" | "emailIntegrations">;

/** Контекстная ссылка из карточек, где вместе показаны разные каналы. */
export function ChannelNavigationMenu({ onNavigate, label = t("servers.add") }: {
  onNavigate: (route: ChannelRoute) => void;
  label?: string;
}) {
  return <Dropdown trigger={["click"]} overlayClassName="app-dropdown" menu={{
    items: [
      { key: "widgets", label: <button type="button"><Icon name="messageCircle" size={16} />{t("navigation.widgets")}</button> },
      { key: "messengers", label: <button type="button"><Icon name="messagesSquare" size={16} />{t("navigation.messengers")}</button> },
      { key: "emailIntegrations", label: <button type="button"><Icon name="mail" size={16} />{t("navigation.mail")}</button> },
    ],
    onClick: ({ key }) => onNavigate(key as ChannelRoute),
  }}>
    <Button className="row-menu-button has-label" variant="secondary" aria-haspopup="menu">
      {label}<Icon name="chevron" size={13} />
    </Button>
  </Dropdown>;
}

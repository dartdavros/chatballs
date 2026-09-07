import { useCallback, useState } from "react";

import { pathFromRoute, type RouteState } from "./router";
import { settingsSectionKey } from "./features/settings/sections";
import {
  DEFAULT_PORTAL_SETTINGS_SECTION,
  portalSettingsSectionKey,
} from "./features/support-portals/sections";
import type { RouteKey } from "./types";

export function useRouteNavigation(
  initialRoute: RouteState,
  organizationPublicId: string | null,
) {
  const [route, setRoute] = useState<RouteKey>(initialRoute.route);
  const [selectedEmployeeId, setSelectedEmployeeId] = useState(initialRoute.employeeId);
  const [selectedProductCode, setSelectedProductCode] = useState(initialRoute.productCode);
  const [selectedAgentId, setSelectedAgentId] = useState(initialRoute.agentId);
  const [selectedKnowledgeId, setSelectedKnowledgeId] = useState(initialRoute.knowledgeId);
  const [selectedConversationId, setSelectedConversationId] = useState<number | null>(null);
  const [selectedClientId, setSelectedClientId] = useState(initialRoute.clientId);
  const [selectedChannelId, setSelectedChannelId] = useState(initialRoute.channelId);
  const [selectedSupportPortalId, setSelectedSupportPortalId] = useState(initialRoute.supportPortalId);
  const [selectedPortalSection, setSelectedPortalSection] = useState(initialRoute.portalSettingsSection);
  const [selectedSettingsSection, setSelectedSettingsSection] = useState(initialRoute.settingsSection);

  const applyRouteState = useCallback((next: RouteState) => {
    setRoute(next.route);
    setSelectedEmployeeId(next.employeeId);
    setSelectedProductCode(next.productCode);
    setSelectedAgentId(next.agentId);
    setSelectedKnowledgeId(next.knowledgeId);
    setSelectedConversationId(null);
    setSelectedClientId(next.clientId);
    setSelectedChannelId(next.channelId);
    setSelectedSupportPortalId(next.supportPortalId);
    setSelectedPortalSection(next.portalSettingsSection);
    setSelectedSettingsSection(next.settingsSection);
  }, []);

  // У «Настроек» второй аргумент — ключ раздела субменю, а не id сущности.
  const navigate = useCallback((
    nextRoute: RouteKey,
    entityId: number | string | null = null,
    replace = false,
    productCode: string | null = null,
    organizationId: string | null = organizationPublicId,
  ) => {
    const nextState: RouteState = {
      organizationPublicId: organizationId,
      route: nextRoute,
      employeeId: nextRoute === "employeeDetail" && typeof entityId === "number" ? entityId : null,
      productCode,
      agentId: nextRoute === "agentDetail" && typeof entityId === "number" ? entityId : null,
      knowledgeId: nextRoute === "aiKnowledgeDetail" && typeof entityId === "number" ? entityId : null,
      clientId: nextRoute === "salesClientDetail" && typeof entityId === "number" ? entityId : null,
      channelId: null,
      supportPortalId: nextRoute === "supportPortalDetail" && typeof entityId === "number"
        ? entityId
        // У настроек портала entityId — «id/раздел»: id портала и ключ раздела.
        : nextRoute === "supportPortalSettings" ? Number(String(entityId).split("/")[0]) || null : null,
      portalSettingsSection: nextRoute === "supportPortalSettings"
        ? portalSettingsSectionKey(String(entityId).split("/")[1] ?? "") ?? DEFAULT_PORTAL_SETTINGS_SECTION
        : null,
      settingsSection: nextRoute === "settings" ? settingsSectionKey(String(entityId)) : null,
    };
    applyRouteState(nextState);
    setSelectedConversationId(
      nextRoute === "chat" && typeof entityId === "number" ? entityId : null,
    );
    const nextPath = pathFromRoute(
      nextRoute,
      entityId,
      nextState.productCode,
      organizationId,
    );
    if (`${window.location.pathname}${window.location.search}` === nextPath) return;
    const method = replace ? "replaceState" : "pushState";
    window.history[method](nextState, "", nextPath);
  }, [applyRouteState, organizationPublicId]);

  return {
    route,
    selectedEmployeeId,
    selectedProductCode,
    selectedAgentId,
    selectedKnowledgeId,
    selectedConversationId,
    selectedClientId,
    selectedChannelId,
    selectedSupportPortalId,
    selectedPortalSection,
    selectedSettingsSection,
    applyRouteState,
    navigate,
  };
}

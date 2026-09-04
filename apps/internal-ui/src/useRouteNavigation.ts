import { useCallback, useState } from "react";

import { pathFromRoute, type RouteState } from "./router";
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
  }, []);

  const navigate = useCallback((
    nextRoute: RouteKey,
    entityId: number | null = null,
    replace = false,
    productCode: string | null = null,
    organizationId: string | null = organizationPublicId,
  ) => {
    const nextState: RouteState = {
      organizationPublicId: organizationId,
      route: nextRoute,
      employeeId: nextRoute === "employeeDetail" ? entityId : null,
      productCode,
      agentId: nextRoute === "agentDetail" ? entityId : null,
      knowledgeId: nextRoute === "aiKnowledgeDetail" ? entityId : null,
      clientId: nextRoute === "salesClientDetail" ? entityId : null,
      channelId: null,
      supportPortalId: nextRoute === "supportPortalDetail" ? entityId : null,
    };
    applyRouteState(nextState);
    setSelectedConversationId(
      nextRoute === "chat" ? entityId : null,
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
    applyRouteState,
    navigate,
  };
}
